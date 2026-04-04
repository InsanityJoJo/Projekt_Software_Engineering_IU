"""Shared fixtures for all integration tests.

This conftest.py lives in tests/integration/ and applies only to
integration tests - not to unit tests in tests/unit/.

Connects to neo4j-test:7687 - both containers run in the same
test_network and resolve each other by container name.

Seed data is imported once manually and frozen in a named volume.
No clean_db needed - stopping the container clears the volume.
"""

import pytest
from src.driver import GraphDBDriver
from src.services.query_builder import AdminQueryBuilder

TEST_NEO4J_URI = "bolt://neo4j-test:7687"
TEST_NEO4J_USER = "neo4j"
TEST_NEO4J_PASSWORD = "testpassword"


@pytest.fixture(scope="session")
def neo4j_driver():
    """Connection to the test Neo4j instance (once per test session).

    scope=session: one connection shared across all integration tests.
    Establishing a Neo4j connection is costly - do not repeat per test.

    No autouse, no effect on unit tests - only instantiated when an
    integration test explicitly requests this fixture.

    pytest.skip() instead of raising an exception so the failure message
    stays readable when the test stack is not running.
    """
    try:
        driver = GraphDBDriver(
            uri=TEST_NEO4J_URI,
            user=TEST_NEO4J_USER,
            password=TEST_NEO4J_PASSWORD,
        )
        result = driver.run_safe_query("RETURN 1 AS test")
        if not result.success:
            pytest.skip(
                f"Neo4j test instance not reachable: {result.error}\n"
                "Start the test stack with: seppt-int"
            )
        yield driver
        driver.close()
    except Exception as e:
        pytest.skip(
            f"Neo4j test instance not reachable: {e}\n"
            "Start the test stack with: seppt-int"
        )


@pytest.fixture
def sample_threat_actor(neo4j_driver):
    """Creates a single ThreatActor node for simple tests."""
    builder = AdminQueryBuilder()
    nodes = [
        {
            "label": "ThreatActor",
            "properties": {
                "name": "APT28",
                "type": "Nation-State",
                "motivation": "Espionage",
                "first_seen": "2015-01-01",
                "last_seen": "2024-01-01",
            },
        }
    ]
    for query, params in builder.merge_nodes_batch(nodes):
        neo4j_driver.execute(query, params, write=True)
    return "APT28"


@pytest.fixture
def sample_graph(neo4j_driver):
    """Creates a small graph for relationship tests.

    Topology:
        APT28 (ThreatActor) -[USES]->    X-Agent (Malware)
        APT28 (ThreatActor) -[TARGETS]-> AcmeCorp (Organization)
        Operation Aurora (Campaign) -[INVOLVES]-> APT28 (ThreatActor)
    """
    builder = AdminQueryBuilder()

    nodes = [
        {"label": "ThreatActor", "properties": {
            "name": "APT28", "type": "Nation-State"
        }},
        {"label": "Malware", "properties": {
            "name": "X-Agent", "family": "Sofacy"
        }},
        {"label": "Organization", "properties": {
            "name": "AcmeCorp", "sector": "Finance"
        }},
        {"label": "Campaign", "properties": {
            "name": "Operation Aurora", "start_date": "2020-01-01"
        }},
    ]
    for query, params in builder.merge_nodes_batch(nodes):
        neo4j_driver.execute(query, params, write=True)

    relationships = [
        {
            "from_label": "ThreatActor", "from_value": "APT28",
            "to_label": "Malware", "to_value": "X-Agent",
            "type": "USES",
        },
        {
            "from_label": "ThreatActor", "from_value": "APT28",
            "to_label": "Organization", "to_value": "AcmeCorp",
            "type": "TARGETS",
        },
        {
            "from_label": "Campaign", "from_value": "Operation Aurora",
            "to_label": "ThreatActor", "to_value": "APT28",
            "type": "INVOLVES",
        },
    ]
    for query, params in builder.merge_relationships_batch(relationships):
        neo4j_driver.execute(query, params, write=True)

    return {"main_node": "APT28", "label": "ThreatActor"}


# ---------------------------------------------------------------------------
# Test ID marker
# ---------------------------------------------------------------------------

def pytest_configure(config):
    """Registers the custom test_id marker."""
    config.addinivalue_line(
        "markers", "test_id(id): unique test ID for the test protocol"
    )

def pytest_collection_modifyitems(items):
    """Prepends the test_id marker value to each item's node ID.

    Runs once after collection, before any output is printed.
    Modifying nodeid here ensures the ID appears in all output
    including the -v test list, the progress line, and the summary.
    """
    for item in items:
        marker = item.get_closest_marker("test_id")
        if marker and marker.args:
            item._nodeid = f"[{marker.args[0]}] {item.nodeid}"

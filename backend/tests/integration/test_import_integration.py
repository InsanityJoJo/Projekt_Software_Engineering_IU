"""Integration tests for ImportService against a real Neo4j instance.

A small number of focused tests - import is infrastructure, not core functionality.
Verifies that data actually arrives in Neo4j, which mock-based tests cannot do.
"""

import json
import pytest

from src.services.import_service import ImportService

pytestmark = pytest.mark.integration

# Unique prefix so import tests do not collide with seed data
_PREFIX = "IMPORT_TEST_"
_ACTOR = f"{_PREFIX}Actor"
_MALWARE = f"{_PREFIX}Malware"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _count(driver, label=None):
    """Count only nodes with _PREFIX - ignores seed data."""
    if label:
        q = (
            f"MATCH (n:{label}) WHERE n.name STARTS WITH '{_PREFIX}' "
            f"RETURN count(n) AS c"
        )
    else:
        q = (
            f"MATCH (n) WHERE n.name STARTS WITH '{_PREFIX}' "
            f"RETURN count(n) AS c"
        )
    return driver.run_safe_query(q).data[0]["c"]


def _count_rels(driver, from_name, rel_type):
    """Count relationships originating from the given node name."""
    result = driver.run_safe_query(
        f"MATCH (n {{name: $name}})-[r:{rel_type}]->() RETURN count(r) AS c",
        {"name": from_name},
    )
    return result.data[0]["c"]


def _get_node(driver, label, name):
    """Read a single node from Neo4j."""
    result = driver.run_safe_query(
        f"MATCH (n:{label} {{name: $name}}) RETURN n",
        {"name": name},
    )
    return result.data[0]["n"] if result.success and result.data else None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def import_service(neo4j_driver):
    return ImportService(neo4j_driver)


@pytest.fixture
def standard_json(tmp_path):
    """JSON file with one ThreatActor, one Malware node, and one USES relationship.

    Uses _PREFIX names to avoid collisions with seed data.
    """
    data = {
        "metadata": {"version": "1.0", "source": "Integration Test"},
        "nodes": [
            {"label": "ThreatActor", "properties": {
                "name": _ACTOR, "type": "Nation-State"
            }},
            {"label": "Malware", "properties": {
                "name": _MALWARE, "family": "TestFamily"
            }},
        ],
        "relationships": [
            {
                "type": "USES",
                "from": {"label": "ThreatActor", "property": "name", "value": _ACTOR},
                "to": {"label": "Malware", "property": "name", "value": _MALWARE},
            }
        ],
    }
    path = tmp_path / "standard.json"
    path.write_text(json.dumps(data))
    return str(path)


@pytest.fixture(autouse=True)
def cleanup_import_test_nodes(neo4j_driver):
    """Deletes IMPORT_TEST_ nodes before and after each test in this file.

    autouse=True applies only within test_import_integration.py, not globally -
    fixtures defined in test files have local scope only.
    """
    neo4j_driver.execute(
        f"MATCH (n) WHERE n.name STARTS WITH '{_PREFIX}' DETACH DELETE n",
        write=True,
    )
    yield
    neo4j_driver.execute(
        f"MATCH (n) WHERE n.name STARTS WITH '{_PREFIX}' DETACH DELETE n",
        write=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestImportServiceNeo4j:
    """Writes data to Neo4j and reads it back - something mock-based tests cannot do."""

    @pytest.mark.test_id("INT-IMP-001")
    def test_nodes_are_persisted_in_neo4j(
        self, neo4j_driver, import_service, standard_json
    ):
        """Smoke test: nodes with _PREFIX are retrievable after import."""
        result = import_service.import_from_json(standard_json, validate=False)

        assert result.success is True
        assert _count(neo4j_driver, "ThreatActor") == 1
        assert _count(neo4j_driver, "Malware") == 1

    @pytest.mark.test_id("INT-IMP-002")
    def test_all_properties_stored_correctly(
        self, neo4j_driver, import_service, tmp_path
    ):
        """Properties arrive in Neo4j unchanged."""
        name = f"{_PREFIX}PropTest"
        data = {
            "metadata": {"version": "1.0"},
            "nodes": [
                {
                    "label": "ThreatActor",
                    "properties": {
                        "name": name,
                        "type": "Nation-State",
                        "motivation": "Espionage",
                        "first_seen": "2015-01-01",
                    },
                }
            ],
            "relationships": [],
        }
        path = tmp_path / "props.json"
        path.write_text(json.dumps(data))

        import_service.import_from_json(str(path), validate=False)

        node = _get_node(neo4j_driver, "ThreatActor", name)
        assert node is not None
        assert node["motivation"] == "Espionage"
        assert node["first_seen"] == "2015-01-01"

    @pytest.mark.test_id("INT-IMP-003")
    def test_relationship_is_created(
        self, neo4j_driver, import_service, standard_json
    ):
        """USES relationship from the _PREFIX actor exists after import."""
        import_service.import_from_json(standard_json, validate=False)

        # from_name is the node name, not the relationship type
        assert _count_rels(neo4j_driver, _ACTOR, "USES") == 1

    @pytest.mark.test_id("INT-IMP-004")
    def test_merge_prevents_duplicates_on_repeated_import(
        self, neo4j_driver, import_service, standard_json
    ):
        """MERGE: importing the same data twice does not create duplicate nodes or edges."""
        import_service.import_from_json(standard_json, validate=False)
        import_service.import_from_json(standard_json, validate=False)

        assert _count(neo4j_driver, "ThreatActor") == 1
        assert _count(neo4j_driver, "Malware") == 1
        assert _count_rels(neo4j_driver, _ACTOR, "USES") == 1

    @pytest.mark.test_id("INT-IMP-005")
    def test_dry_run_writes_nothing_to_neo4j(
        self, neo4j_driver, import_service, standard_json
    ):
        """dry_run=True: no node with _PREFIX exists in the database afterwards."""
        result = import_service.import_from_json(standard_json, dry_run=True)

        assert result.success is True
        # Counts only _PREFIX nodes, not seed data
        assert _count(neo4j_driver) == 0

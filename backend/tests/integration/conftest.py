"""Geteilte Fixtures fuer alle Integrationstests.

Diese conftest.py liegt in tests/integration/ und gilt nur fuer
Integrationstests - nicht fuer Unit-Tests in tests/unit/.

Verbindet sich zu neo4j-test:7687 - beide Container laufen im
selben test_network und finden sich per Containername.

Seed-Daten werden einmalig manuell importiert und per tmpfs
eingefroren. Kein clean_db noetig - tmpfs garantiert sauberen
Zustand pro Test-Session (Container-Stop = Daten weg).
"""

import pytest
from src.driver import GraphDBDriver
from src.services.query_builder import AdminQueryBuilder

TEST_NEO4J_URI = "bolt://neo4j-test:7687"
TEST_NEO4J_USER = "neo4j"
TEST_NEO4J_PASSWORD = "testpassword"


@pytest.fixture(scope="session")
def neo4j_driver():
    """Verbindung zur Test-Neo4j-Instanz (einmal pro Test-Session).

    scope=session: eine Verbindung fuer alle Integrationstests zusammen.
    Neo4j-Verbindungsaufbau kostet Zeit - nicht pro Test wiederholen.

    Kein autouse, kein Einfluss auf Unit-Tests - wird nur instanziiert
    wenn ein Integrationstest sie explizit anfordert.

    pytest.skip() statt Exception damit der Fehler lesbar bleibt
    wenn der Test-Stack nicht laeuft.
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
                f"Neo4j Test-Instanz nicht erreichbar: {result.error}\n"
                "Starte den Test-Stack mit: seppt-int"
            )
        yield driver
        driver.close()
    except Exception as e:
        pytest.skip(
            f"Neo4j Test-Instanz nicht erreichbar: {e}\n"
            "Starte den Test-Stack mit: seppt-int"
        )
 

@pytest.fixture
def sample_threat_actor(neo4j_driver):
    """Erstellt einen einzelnen ThreatActor-Node fuer einfache Tests."""
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
    """Erstellt einen kleinen Graphen fuer Relationship-Tests.

    Topologie:
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
  

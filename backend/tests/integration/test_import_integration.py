"""Integrationstests fuer ImportService gegen echte Neo4j-Instanz.

Wenige, fokussierte Tests - Import ist Infrastruktur, nicht Kernfunktion.
Verifiziert dass Daten tatsaechlich in Neo4j ankommen, was Mock-Tests
nicht koennen.
"""

import json
import pytest

from src.services.import_service import ImportService

pytestmark = pytest.mark.integration

# Eindeutiger Prefix damit Import-Tests nicht mit Seed-Daten kollidieren
_PREFIX = "IMPORT_TEST_"
_ACTOR = f"{_PREFIX}Actor"
_MALWARE = f"{_PREFIX}Malware"


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _count(driver, label=None):
    """Zaehlt nur Nodes mit _PREFIX - ignoriert Seed-Daten."""
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
    """Zaehlt Relationships vom angegebenen Node-Namen."""
    result = driver.run_safe_query(
        f"MATCH (n {{name: $name}})-[r:{rel_type}]->() RETURN count(r) AS c",
        {"name": from_name},
    )
    return result.data[0]["c"]


def _get_node(driver, label, name):
    """Liest einen einzelnen Node aus Neo4j."""
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
    """JSON-Datei mit einem ThreatActor, einem Malware-Node und einer USES-Relation.

    Verwendet _PREFIX-Namen damit keine Kollision mit Seed-Daten entsteht.
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
    """Loescht IMPORT_TEST_-Nodes vor und nach jedem Test in dieser Datei.

    autouse=True gilt hier nur fuer Tests in test_import_integration.py,
    nicht global - Fixtures in Testdateien haben nur lokalen Scope.
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
    """Schreibt Daten in Neo4j und liest sie zurueck - das koennen Mocks nicht."""

    def test_nodes_landen_wirklich_in_neo4j(
        self, neo4j_driver, import_service, standard_json
    ):
        """Smoke-Test: Nodes mit _PREFIX sind nach dem Import auffindbar."""
        result = import_service.import_from_json(standard_json, validate=False)

        assert result.success is True
        assert _count(neo4j_driver, "ThreatActor") == 1
        assert _count(neo4j_driver, "Malware") == 1

    def test_alle_properties_korrekt_gespeichert(
        self, neo4j_driver, import_service, tmp_path
    ):
        """Properties kommen unveraendert in Neo4j an."""
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

    def test_relationship_wird_erstellt(
        self, neo4j_driver, import_service, standard_json
    ):
        """USES-Relationship vom _PREFIX-Actor existiert nach dem Import."""
        import_service.import_from_json(standard_json, validate=False)

        # from_name ist der Node-Name, nicht der Relationship-Typ
        assert _count_rels(neo4j_driver, _ACTOR, "USES") == 1

    def test_merge_verhindert_duplikate_bei_wiederholtem_import(
        self, neo4j_driver, import_service, standard_json
    ):
        """MERGE: zweifacher Import erzeugt keine doppelten Nodes oder Kanten."""
        import_service.import_from_json(standard_json, validate=False)
        import_service.import_from_json(standard_json, validate=False)

        assert _count(neo4j_driver, "ThreatActor") == 1
        assert _count(neo4j_driver, "Malware") == 1
        assert _count_rels(neo4j_driver, _ACTOR, "USES") == 1

    def test_dry_run_schreibt_nichts_in_neo4j(
        self, neo4j_driver, import_service, standard_json
    ):
        """dry_run=True: kein Node mit _PREFIX in der DB danach."""
        result = import_service.import_from_json(standard_json, dry_run=True)

        assert result.success is True
        # Zaehlt nur _PREFIX-Nodes, nicht die Seed-Daten
        assert _count(neo4j_driver) == 0

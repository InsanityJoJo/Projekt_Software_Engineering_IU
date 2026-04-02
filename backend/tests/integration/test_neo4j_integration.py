"""Integrationstests fuer AutocompleteService und SafeQueryBuilder.

Testet Query-Logik gegen echte Neo4j-Instanz im Docker-Netzwerk.
Fixtures kommen aus conftest.py in diesem Verzeichnis.
"""

import pytest
from src.services.autocomplete_service import AutocompleteService
from src.services.query_builder import AdminQueryBuilder, SafeQueryBuilder

pytestmark = pytest.mark.integration


class TestAutocompleteIntegration:
    """AutocompleteService gegen echte Neo4j-Instanz."""

    def test_prefix_match_findet_korrekten_node(
        self, neo4j_driver, sample_threat_actor
    ):
        """Prefix 'APT' findet 'APT28'."""
        service = AutocompleteService(neo4j_driver)

        result = service.suggest_node_names(prefix="APT")

        assert result.success is True
        assert len(result.data) >= 1
        names = [item["name"] for item in result.data]
        assert "APT28" in names

    def test_prefix_match_ist_case_insensitiv(
        self, neo4j_driver, sample_threat_actor
    ):
        """'apt' und 'APT' liefern identische Treffer."""
        service = AutocompleteService(neo4j_driver)

        result_lower = service.suggest_node_names(prefix="apt")
        result_upper = service.suggest_node_names(prefix="APT")

        assert result_lower.success is True
        assert result_upper.success is True
        assert (
            {item["name"] for item in result_lower.data}
            == {item["name"] for item in result_upper.data}
        )

    def test_kein_treffer_gibt_leere_liste(
        self, neo4j_driver, sample_threat_actor
    ):
        """Unbekannter Prefix -> leere Liste, kein Fehler."""
        service = AutocompleteService(neo4j_driver)

        result = service.suggest_node_names(prefix="XYZ_NONEXISTENT_999")

        assert result.success is True
        assert len(result.data) == 0

    def test_label_filter_schraenkt_ergebnisse_ein(self, neo4j_driver):
        """label='ThreatActor' schliesst Malware- und Campaign-Nodes aus."""
        builder = AdminQueryBuilder()
        nodes = [
            {"label": "ThreatActor", "properties": {"name": "AlphaGroup"}},
            {"label": "Malware", "properties": {"name": "AlphaBot"}},
            {"label": "Campaign", "properties": {"name": "AlphaOperation"}},
        ]
        for query, params in builder.merge_nodes_batch(nodes):
            neo4j_driver.execute(query, params, write=True)

        service = AutocompleteService(neo4j_driver)
        result = service.suggest_node_names(prefix="Alpha", label="ThreatActor")

        assert result.success is True
        assert len(result.data) >= 1
        assert all(item["label"] == "ThreatActor" for item in result.data)
        names = [item["name"] for item in result.data]
        assert "AlphaGroup" in names
        assert "AlphaBot" not in names
        assert "AlphaOperation" not in names

    def test_limit_wird_eingehalten(self, neo4j_driver):
        """limit=3 liefert hoechstens 3 Ergebnisse, auch bei 10 Nodes."""
        builder = AdminQueryBuilder()
        nodes = [
            {"label": "ThreatActor", "properties": {"name": f"TestActor{i:02d}"}}
            for i in range(10)
        ]
        for query, params in builder.merge_nodes_batch(nodes):
            neo4j_driver.execute(query, params, write=True)

        service = AutocompleteService(neo4j_driver)
        result = service.suggest_node_names(prefix="TestActor", limit=3)

        assert result.success is True
        assert len(result.data) <= 3

    def test_fuzzy_search_findet_substring(
        self, neo4j_driver, sample_threat_actor
    ):
        """'PT2' ist Substring von 'APT28' und wird per fuzzy_search gefunden."""
        service = AutocompleteService(neo4j_driver)

        result = service.fuzzy_search(search_term="PT2")

        assert result.success is True
        names = [item["name"] for item in result.data]
        assert "APT28" in names

    def test_ergebnis_enthaelt_pflichtfelder_fuer_ui(
        self, neo4j_driver, sample_threat_actor
    ):
        """Jedes Ergebnis hat 'name', 'label', 'id' - benoetigt vom Frontend."""
        service = AutocompleteService(neo4j_driver)

        result = service.suggest_node_names(prefix="APT")

        assert result.success is True
        assert len(result.data) > 0
        for item in result.data:
            assert "name" in item, f"Feld 'name' fehlt in: {item}"
            assert "label" in item, f"Feld 'label' fehlt in: {item}"
            assert "id" in item, f"Feld 'id' fehlt in: {item}"


class TestNodeByNameHopsIntegration:
    """find_connected_nodes mit verschiedenen Hop-Tiefen gegen echte Neo4j."""

    def test_hops_null_gibt_nur_startnode(self, neo4j_driver, sample_graph):
        """hops=0: nur der angefragte Node, 'connected' ist immer None."""
        builder = SafeQueryBuilder()
        query, params = builder.find_connected_nodes(
            start_label="ThreatActor",
            start_property="name",
            start_value="APT28",
            max_hops=0,
        )
        result = neo4j_driver.run_safe_query(query, params)

        assert result.success is True
        assert len(result.data) >= 1
        assert all(r.get("connected") is None for r in result.data)

    def test_hops_eins_gibt_direkte_nachbarn(self, neo4j_driver, sample_graph):
        """hops=1: X-Agent und AcmeCorp sind direkte Nachbarn von APT28."""
        builder = SafeQueryBuilder()
        query, params = builder.find_connected_nodes(
            start_label="ThreatActor",
            start_property="name",
            start_value="APT28",
            max_hops=1,
        )
        result = neo4j_driver.run_safe_query(query, params)

        assert result.success is True
        connected_names = {
            r["connected"]["name"]
            for r in result.data
            if r.get("connected") is not None
        }
        assert "X-Agent" in connected_names
        assert "AcmeCorp" in connected_names

    def test_hops_zwei_findet_indirekte_verbindungen(self, neo4j_driver):
        """hops=2: Kette APT28 -> X-Agent -> CVE wird vollstaendig traversiert."""
        builder = AdminQueryBuilder()
        nodes = [
            {"label": "ThreatActor", "properties": {"name": "APT28"}},
            {"label": "Malware", "properties": {"name": "X-Agent"}},
            {"label": "Vulnerability", "properties": {
                "name": "CVE-2021-1234", "cve_id": "CVE-2021-1234"
            }},
        ]
        for query, params in builder.merge_nodes_batch(nodes):
            neo4j_driver.execute(query, params, write=True)

        rels = [
            {
                "from_label": "ThreatActor", "from_value": "APT28",
                "to_label": "Malware", "to_value": "X-Agent",
                "type": "USES",
            },
            {
                "from_label": "Malware", "from_value": "X-Agent",
                "to_label": "Vulnerability", "to_value": "CVE-2021-1234",
                "type": "USES",
            },
        ]
        for query, params in builder.merge_relationships_batch(rels):
            neo4j_driver.execute(query, params, write=True)

        sq = SafeQueryBuilder()
        query, params = sq.find_connected_nodes(
            start_label="ThreatActor",
            start_property="name",
            start_value="APT28",
            max_hops=2,
        )
        result = neo4j_driver.run_safe_query(query, params)

        assert result.success is True
        all_connected = {
            r["connected"]["name"]
            for r in result.data
            if r.get("connected") is not None
        }
        assert "CVE-2021-1234" in all_connected

    def test_isolierter_node_wird_zurueckgegeben(self, neo4j_driver):
        """Node ohne Verbindungen liefert Ergebnis dank OPTIONAL MATCH."""
        builder = AdminQueryBuilder()
        nodes = [{"label": "ThreatActor", "properties": {"name": "LoneWolf"}}]
        for query, params in builder.merge_nodes_batch(nodes):
            neo4j_driver.execute(query, params, write=True)

        sq = SafeQueryBuilder()
        query, params = sq.find_connected_nodes(
            start_label="ThreatActor",
            start_property="name",
            start_value="LoneWolf",
            max_hops=1,
        )
        result = neo4j_driver.run_safe_query(query, params)

        assert result.success is True
        assert len(result.data) >= 1
        assert result.data[0]["start"]["name"] == "LoneWolf"
        assert result.data[0].get("connected") is None

    def test_nicht_existierender_node_gibt_leere_liste(self, neo4j_driver):
        """Anfrage fuer unbekannten Node -> leere Liste, kein Fehler."""
        sq = SafeQueryBuilder()
        query, params = sq.find_connected_nodes(
            start_label="ThreatActor",
            start_property="name",
            start_value="EXISTIERT_NICHT",
            max_hops=1,
        )
        result = neo4j_driver.run_safe_query(query, params)

        assert result.success is True
        assert len(result.data) == 0

    def test_relationship_typ_in_ergebnis_enthalten(
        self, neo4j_driver, sample_graph
    ):
        """relationship_details enthaelt die Typen der Kanten."""
        sq = SafeQueryBuilder()
        query, params = sq.find_connected_nodes(
            start_label="ThreatActor",
            start_property="name",
            start_value="APT28",
            max_hops=1,
        )
        result = neo4j_driver.run_safe_query(query, params)

        assert result.success is True
        rel_types = {
            detail.get("type")
            for record in result.data
            for detail in record.get("relationship_details", [])
        }
        assert "USES" in rel_types or "TARGETS" in rel_types

"""Integration tests for AutocompleteService and SafeQueryBuilder.

Tests query logic against a real Neo4j instance running in the Docker network.
Fixtures are provided by conftest.py in this directory.
"""

import pytest
from src.services.autocomplete_service import AutocompleteService
from src.services.query_builder import AdminQueryBuilder, SafeQueryBuilder

pytestmark = pytest.mark.integration


class TestAutocompleteIntegration:
    """AutocompleteService against a real Neo4j instance."""

    @pytest.mark.test_id("INT-AC-001")
    def test_prefix_match_returns_correct_node(
        self, neo4j_driver, sample_threat_actor
    ):
        """Prefix 'APT' finds 'APT28'."""
        service = AutocompleteService(neo4j_driver)

        result = service.suggest_node_names(prefix="APT")

        assert result.success is True
        assert len(result.data) >= 1
        names = [item["name"] for item in result.data]
        assert "APT28" in names

    @pytest.mark.test_id("INT-AC-002")
    def test_prefix_match_is_case_insensitive(
        self, neo4j_driver, sample_threat_actor
    ):
        """'apt' and 'APT' return identical results."""
        service = AutocompleteService(neo4j_driver)

        result_lower = service.suggest_node_names(prefix="apt")
        result_upper = service.suggest_node_names(prefix="APT")

        assert result_lower.success is True
        assert result_upper.success is True
        assert (
            {item["name"] for item in result_lower.data}
            == {item["name"] for item in result_upper.data}
        )

    @pytest.mark.test_id("INT-AC-003")
    def test_no_match_returns_empty_list(
        self, neo4j_driver, sample_threat_actor
    ):
        """Unknown prefix returns an empty list without raising an error."""
        service = AutocompleteService(neo4j_driver)

        result = service.suggest_node_names(prefix="XYZ_NONEXISTENT_999")

        assert result.success is True
        assert len(result.data) == 0

    @pytest.mark.test_id("INT-AC-004")
    def test_label_filter_restricts_results(self, neo4j_driver):
        """label='ThreatActor' excludes Malware and Campaign nodes."""
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

    @pytest.mark.test_id("INT-AC-005")
    def test_limit_parameter_is_respected(self, neo4j_driver):
        """limit=3 returns at most 3 results even when 10 nodes match."""
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

    @pytest.mark.test_id("INT-AC-006")
    def test_fuzzy_search_finds_substring(
        self, neo4j_driver, sample_threat_actor
    ):
        """'PT2' is a substring of 'APT28' and is found via fuzzy_search."""
        service = AutocompleteService(neo4j_driver)

        result = service.fuzzy_search(search_term="PT2")

        assert result.success is True
        names = [item["name"] for item in result.data]
        assert "APT28" in names

    @pytest.mark.test_id("INT-AC-007")
    def test_result_contains_required_frontend_fields(
        self, neo4j_driver, sample_threat_actor
    ):
        """Every result contains 'name', 'label', 'id' as required by the frontend."""
        service = AutocompleteService(neo4j_driver)

        result = service.suggest_node_names(prefix="APT")

        assert result.success is True
        assert len(result.data) > 0
        for item in result.data:
            assert "name" in item, f"Field 'name' missing in: {item}"
            assert "label" in item, f"Field 'label' missing in: {item}"
            assert "id" in item, f"Field 'id' missing in: {item}"


class TestNodeByNameHopsIntegration:
    """find_connected_nodes with varying hop depths against a real Neo4j instance."""

    @pytest.mark.test_id("INT-HOP-001")
    def test_hops_zero_returns_only_start_node(self, neo4j_driver, sample_graph):
        """hops=0: only the requested node is returned, 'connected' is always None."""
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

    @pytest.mark.test_id("INT-HOP-002")
    def test_hops_one_returns_direct_neighbors(self, neo4j_driver, sample_graph):
        """hops=1: X-Agent and AcmeCorp are direct neighbors of APT28."""
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

    @pytest.mark.test_id("INT-HOP-003")
    def test_hops_two_finds_indirect_connections(self, neo4j_driver):
        """hops=2: chain APT28 -> X-Agent -> CVE is fully traversed."""
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

    @pytest.mark.test_id("INT-HOP-004")
    def test_isolated_node_is_returned(self, neo4j_driver):
        """Node without relationships is still returned due to OPTIONAL MATCH."""
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

    @pytest.mark.test_id("INT-HOP-005")
    def test_nonexistent_node_returns_empty_list(self, neo4j_driver):
        """Query for an unknown node returns an empty list without raising an error."""
        sq = SafeQueryBuilder()
        query, params = sq.find_connected_nodes(
            start_label="ThreatActor",
            start_property="name",
            start_value="DOES_NOT_EXIST",
            max_hops=1,
        )
        result = neo4j_driver.run_safe_query(query, params)

        assert result.success is True
        assert len(result.data) == 0

    @pytest.mark.test_id("INT-HOP-006")
    def test_relationship_type_included_in_result(
        self, neo4j_driver, sample_graph
    ):
        """relationship_details contains the types of the traversed edges."""
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

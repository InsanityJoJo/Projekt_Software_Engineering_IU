"""Unit tests for the SafeQueryBuilder class.

This module tests the query builder's ability to create safe,
parameterized Cypher queries and prevent injection attacks.
"""

import pytest
from src.services.query_builder import (
    SafeQueryBuilder,
    AdminQueryBuilder,
    QueryValidationError,
)


class TestQueryBuilderValidation:
    """Test suite for validation methods."""

    def test_validate_allowed_label(self):
        """Test that allowed labels pass validation."""
        builder = SafeQueryBuilder()
        assert builder.validate_label("ThreatActor") == "ThreatActor"

    def test_validate_disallowed_label(self):
        """Test that disallowed labels raise error."""
        builder = SafeQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.validate_label("MaliciousLabel")

    def test_validate_allowed_relationship(self):
        """Test that allowed relationships pass validation."""
        builder = SafeQueryBuilder()
        assert builder.validate_relationship("BASED_ON") == "BASED_ON"

    def test_validate_disallowed_relationship(self):
        """Test that disallowed relationships raise error."""
        builder = SafeQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.validate_relationship("MALICIOUS_REL")

    def test_validate_allowed_property(self):
        """Test that allowed properties pass validation."""
        builder = SafeQueryBuilder()
        assert builder.validate_property("name") == "name"

    def test_validate_disallowed_property(self):
        """Test that disallowed properties raise error."""
        builder = SafeQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.validate_property("malicious_prop")


class TestQueryBuilderSafety:
    """Test suite for query safety checks."""

    def test_detect_delete_keyword(self):
        """Test that DELETE keyword is detected and blocked."""
        builder = SafeQueryBuilder()
        malicious_query = "MATCH (n) DELETE n"

        with pytest.raises(QueryValidationError) as exc_info:
            builder.validate_query_safety(malicious_query)

        assert "DELETE" in str(exc_info.value)

    def test_detect_create_keyword(self):
        """Test that CREATE keyword is detected and blocked."""
        builder = SafeQueryBuilder()
        malicious_query = "CREATE (n:Tool {name: 'hack'})"

        with pytest.raises(QueryValidationError):
            builder.validate_query_safety(malicious_query)

    def test_detect_remove_keyword(self):
        """Test that REMOVE keyword is detected and blocked."""
        builder = SafeQueryBuilder()
        malicious_query = "MATCH (n) REMOVE n.important_prop"

        with pytest.raises(QueryValidationError):
            builder.validate_query_safety(malicious_query)

    def test_allow_safe_read_query(self):
        """Test that safe read queries pass validation."""
        builder = SafeQueryBuilder()
        safe_query = "MATCH (n:Tool) RETURN n LIMIT 10"

        # Should not raise any exception
        builder.validate_query_safety(safe_query)


class TestFindNodeByProperty:
    """Test suite for find_node_by_property method."""

    def test_build_simple_query(self):
        """Test building a simple node search query."""
        builder = SafeQueryBuilder()
        query, params = builder.find_node_by_property(
            label="ThreatActor", property_name="name", property_value="Alice"
        )

        assert "MATCH (n:ThreatActor {name: $value})" in query
        assert params["value"] == "Alice"
        assert "LIMIT" in query

    def test_build_query_with_specific_properties(self):
        """Test query with specific return properties."""
        builder = SafeQueryBuilder()
        query, params = builder.find_node_by_property(
            label="ThreatActor",
            property_name="name",
            property_value="Alice",
            return_properties=["name", "type"],
        )

        assert "n.name AS name" in query
        assert "n.type AS type" in query

    def test_reject_invalid_label(self):
        """Test that invalid label is rejected."""
        builder = SafeQueryBuilder()

        with pytest.raises(QueryValidationError):
            builder.find_node_by_property(
                label="InvalidLabel", property_name="name", property_value="Alice"
            )

    def test_reject_invalid_property(self):
        """Test that invalid property is rejected."""
        builder = SafeQueryBuilder()

        with pytest.raises(QueryValidationError):
            builder.find_node_by_property(
                label="ThreatActor",
                property_name="invalid_prop",
                property_value="Alice",
            )

    def test_custom_limit(self):
        """Test that custom limit is applied."""
        builder = SafeQueryBuilder()
        query, params = builder.find_node_by_property(
            label="ThreatActor", property_name="name", property_value="Alice", limit=5
        )

        assert params["limit"] == 5


class TestFindConnectedNodes:
    """Test suite for find_connected_nodes method."""

    def test_build_single_hop_query(self):
        """Test building a single-hop traversal query."""
        builder = SafeQueryBuilder()
        query, params = builder.find_connected_nodes(
            start_label="ThreatActor",
            start_property="name",
            start_value="Alice",
            max_hops=1,
        )

        assert "MATCH path = (start:ThreatActor {name: $start_value})" in query
        assert "[r*1..1]" in query
        assert params["start_value"] == "Alice"

    def test_build_multi_hop_query(self):
        """Test building a multi-hop traversal query."""
        builder = SafeQueryBuilder()
        query, params = builder.find_connected_nodes(
            start_label="ThreatActor",
            start_property="name",
            start_value="Alice",
            max_hops=3,
        )

        assert "[r*1..3]" in query

    def test_build_query_with_specific_relationship(self):
        """Test query with specific relationship type."""
        builder = SafeQueryBuilder()
        query, params = builder.find_connected_nodes(
            start_label="ThreatActor",
            start_property="name",
            start_value="Alice",
            relationship_type="BASED_ON",
            max_hops=2,
        )

        assert "[r:BASED_ON*1..2]" in query

    def test_reject_excessive_hops(self):
        """Test that excessive hops are rejected."""
        builder = SafeQueryBuilder()

        with pytest.raises(QueryValidationError) as exc_info:
            builder.find_connected_nodes(
                start_label="ThreatActor",
                start_property="name",
                start_value="Alice",
                max_hops=5,
            )

        assert "max_hops must be between 1 and 3" in str(exc_info.value)

    def test_reject_zero_hops(self):
        """Test that zero hops are rejected."""
        builder = SafeQueryBuilder()

        with pytest.raises(QueryValidationError):
            builder.find_connected_nodes(
                start_label="ThreatActor",
                start_property="name",
                start_value="Alice",
                max_hops=0,
            )


class TestGetNodeWithRelationships:
    """Test suite for get_node_with_relationships method."""

    def test_build_query_all_relationships(self):
        """Test building query to get node with all relationships."""
        builder = SafeQueryBuilder()
        query, params = builder.get_node_with_relationships(
            label="ThreatActor", property_name="name", property_value="Alice"
        )

        assert "MATCH (n:ThreatActor {name: $value})" in query
        assert "OPTIONAL MATCH (n)-[r]-(connected)" in query
        assert "collect(" in query
        assert params["value"] == "Alice"

    def test_build_query_specific_relationship(self):
        """Test query with specific relationship type filter."""
        builder = SafeQueryBuilder()
        query, params = builder.get_node_with_relationships(
            label="ThreatActor",
            property_name="name",
            property_value="Alice",
            relationship_type="BASED_ON",
        )

        assert "[r:BASED_ON]" in query

    def test_includes_relationship_direction(self):
        """Test that query includes relationship direction."""
        builder = SafeQueryBuilder()
        query, params = builder.get_node_with_relationships(
            label="ThreatActor", property_name="name", property_value="Alice"
        )

        assert "direction" in query
        assert "incoming" in query
        assert "outgoing" in query


class TestSearchNodes:
    """Test suite for search_nodes method."""

    def test_exact_match(self):
        """Test building exact match search query."""
        builder = SafeQueryBuilder()
        query, params = builder.search_nodes(
            label="ThreatActor",
            search_property="name",
            search_value="Alice",
            match_type="exact",
        )

        assert "n.name = $search_value" in query
        assert params["search_value"] == "Alice"

    def test_starts_with_match(self):
        """Test building starts_with search query."""
        builder = SafeQueryBuilder()
        query, params = builder.search_nodes(
            label="ThreatActor",
            search_property="name",
            search_value="Ali",
            match_type="starts_with",
        )

        assert "STARTS WITH" in query
        assert "toLower" in query

    def test_contains_match(self):
        """Test building contains search query."""
        builder = SafeQueryBuilder()
        query, params = builder.search_nodes(
            label="ThreatActor",
            search_property="name",
            search_value="lic",
            match_type="contains",
        )

        assert "CONTAINS" in query
        assert "toLower" in query

    def test_search_without_label(self):
        """Test search across all node types."""
        builder = SafeQueryBuilder()
        query, params = builder.search_nodes(
            search_property="name", search_value="Alice", match_type="exact"
        )

        assert "MATCH (n)" in query
        assert ":ThreatActor" not in query

    def test_invalid_match_type(self):
        """Test that invalid match type is rejected."""
        builder = SafeQueryBuilder()

        with pytest.raises(QueryValidationError) as exc_info:
            builder.search_nodes(
                search_property="name", search_value="Alice", match_type="invalid_type"
            )

        assert "Invalid match_type" in str(exc_info.value)

    def test_search_includes_limit(self):
        """Test that search queries include limit."""
        builder = SafeQueryBuilder()
        query, params = builder.search_nodes(
            search_property="name", search_value="Alice", match_type="exact", limit=25
        )

        assert "LIMIT" in query
        assert params["limit"] == 25

    def test_default_limit_applied(self):
        """Test that default limit is applied when not specified."""
        builder = SafeQueryBuilder(max_results=50)
        query, params = builder.search_nodes(
            search_property="name", search_value="Alice", match_type="exact"
        )

        assert params["limit"] == 50


class TestParameterization:
    """Test suite for proper parameterization (injection prevention)."""

    def test_values_are_parameterized(self):
        """Test that all values are passed as parameters, not in query string."""
        builder = SafeQueryBuilder()

        # Attempt SQL-injection-style attack
        malicious_value = "'; DELETE (n); //"

        query, params = builder.find_node_by_property(
            label="ThreatActor", property_name="name", property_value=malicious_value
        )

        # Value should be in params, not in query string
        assert malicious_value not in query
        assert params["value"] == malicious_value

    def test_search_values_are_parameterized(self):
        """Test that search values are parameterized."""
        builder = SafeQueryBuilder()

        malicious_search = "admin' OR 1=1 --"
        query, params = builder.search_nodes(
            search_property="name", search_value=malicious_search, match_type="exact"
        )

        # Malicious string should be in params, not query
        assert malicious_search not in query
        assert params["search_value"] == malicious_search


class TestMaxResultsLimit:
    """Test suite for result limiting."""

    def test_default_max_results(self):
        """Test that default max_results is applied."""
        builder = SafeQueryBuilder()
        query, params = builder.find_node_by_property(
            label="ThreatActor", property_name="name", property_value="Alice"
        )

        assert params["limit"] == 100  # default

    def test_custom_max_results(self):
        """Test that custom max_results is applied."""
        builder = SafeQueryBuilder(max_results=25)
        query, params = builder.find_node_by_property(
            label="ThreatActor", property_name="name", property_value="Alice"
        )

        assert params["limit"] == 25

    def test_explicit_limit_overrides_default(self):
        """Test that explicit limit overrides default max_results."""
        builder = SafeQueryBuilder(max_results=100)
        query, params = builder.find_node_by_property(
            label="ThreatActor", property_name="name", property_value="Alice", limit=10
        )

        assert params["limit"] == 10


# AdminQueryBuilder Tests


class TestAdminQueryBuilderInit:
    """Test suite for AdminQueryBuilder initialization."""

    def test_inherits_from_safe_query_builder(self):
        """Test that AdminQueryBuilder inherits from SafeQueryBuilder."""
        builder = AdminQueryBuilder()
        assert isinstance(builder, SafeQueryBuilder)

    def test_init_sets_default_max_results(self):
        """Test that initialization sets default max_results."""
        builder = AdminQueryBuilder()
        assert builder.max_results == 100

    def test_init_accepts_custom_max_results(self):
        """Test that initialization accepts custom max_results."""
        builder = AdminQueryBuilder(max_results=50)
        assert builder.max_results == 50


class TestAdminQueryBuilderSafety:
    """Test suite for AdminQueryBuilder safety override."""

    def test_allows_write_keywords(self):
        """Test that validate_query_safety allows write keywords."""
        builder = AdminQueryBuilder()

        # Should not raise any exceptions
        builder.validate_query_safety("CREATE (n:Test)")
        builder.validate_query_safety("MERGE (n:Test)")
        builder.validate_query_safety("DELETE n")
        builder.validate_query_safety("SET n.prop = 'value'")
        builder.validate_query_safety("REMOVE n.prop")

    def test_still_validates_labels(self):
        """Test that label validation still works."""
        builder = AdminQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.validate_label("InvalidLabel")

    def test_still_validates_properties(self):
        """Test that property validation still works."""
        builder = AdminQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.validate_property("invalid_prop")

    def test_still_validates_relationships(self):
        """Test that relationship validation still works."""
        builder = AdminQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.validate_relationship("INVALID_REL")


class TestAdminMergeNode:
    """Test suite for merge_node method."""

    def test_merge_node_basic(self):
        """Test basic node merge with match properties only."""
        builder = AdminQueryBuilder()
        query, params = builder.merge_node("ThreatActor", {"name": "APT28"})

        assert "MERGE (n:ThreatActor {name: $match_name})" in query
        assert params["match_name"] == "APT28"
        assert "RETURN n" in query

    def test_merge_node_with_set_properties(self):
        """Test node merge with additional set properties."""
        builder = AdminQueryBuilder()
        query, params = builder.merge_node(
            "ThreatActor",
            {"name": "APT28"},
            {"type": "Nation-State", "last_seen": "2024-01-01"},
        )

        assert "MERGE (n:ThreatActor {name: $match_name})" in query
        assert "SET n += $set_properties" in query
        assert params["match_name"] == "APT28"
        assert params["set_properties"] == {
            "type": "Nation-State",
            "last_seen": "2024-01-01",
        }

    def test_merge_node_multiple_match_properties(self):
        """Test node merge with multiple match properties."""
        builder = AdminQueryBuilder()
        query, params = builder.merge_node(
            "Observable", {"name": "malicious.exe", "type": "file"}
        )

        assert "MERGE (n:Observable" in query
        assert "match_name" in params
        assert "match_type" in params

    def test_merge_node_validates_label(self):
        """Test that merge_node validates labels."""
        builder = AdminQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.merge_node("InvalidLabel", {"name": "test"})

    def test_merge_node_validates_match_properties(self):
        """Test that merge_node validates match properties."""
        builder = AdminQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.merge_node("ThreatActor", {"invalid_prop": "test"})

    def test_merge_node_validates_set_properties(self):
        """Test that merge_node validates set properties."""
        builder = AdminQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.merge_node(
                "ThreatActor", {"name": "APT28"}, {"invalid_prop": "test"}
            )

    def test_merge_node_requires_match_properties(self):
        """Test that merge_node requires non-empty match_properties."""
        builder = AdminQueryBuilder()
        with pytest.raises(QueryValidationError) as exc_info:
            builder.merge_node("ThreatActor", {})

        assert "match_properties cannot be empty" in str(exc_info.value)


class TestAdminMergeNodesBatch:
    """Test suite for merge_nodes_batch method."""

    def test_merge_nodes_batch_basic(self):
        """Test basic batch node merge."""
        builder = AdminQueryBuilder()
        nodes = [
            {
                "label": "ThreatActor",
                "properties": {"name": "APT28", "type": "Nation-State"},
            },
            {"label": "Malware", "properties": {"name": "X-Agent", "family": "Sofacy"}},
        ]

        query, params = builder.merge_nodes_batch(nodes)

        assert "UNWIND $nodes AS nodeData" in query
        assert "MERGE (n:$(nodeData.label) {name: nodeData.properties.name})" in query
        assert "SET n += nodeData.properties" in query
        assert params["nodes"] == nodes

    def test_merge_nodes_batch_custom_match_property(self):
        """Test batch merge with custom match property."""
        builder = AdminQueryBuilder()
        nodes = [
            {
                "label": "Vulnerability",
                "properties": {"cve_id": "CVE-2024-1234", "cvss_score": "9.8"},
            }
        ]

        query, params = builder.merge_nodes_batch(nodes, match_property="cve_id")

        assert "{cve_id: nodeData.properties.cve_id}" in query

    def test_merge_nodes_batch_validates_labels(self):
        """Test that batch merge validates all labels."""
        builder = AdminQueryBuilder()
        nodes = [
            {"label": "ThreatActor", "properties": {"name": "APT28"}},
            {"label": "InvalidLabel", "properties": {"name": "Test"}},
        ]

        with pytest.raises(QueryValidationError):
            builder.merge_nodes_batch(nodes)

    def test_merge_nodes_batch_validates_properties(self):
        """Test that batch merge validates all properties."""
        builder = AdminQueryBuilder()
        nodes = [
            {
                "label": "ThreatActor",
                "properties": {"name": "APT28", "invalid_prop": "test"},
            }
        ]

        with pytest.raises(QueryValidationError):
            builder.merge_nodes_batch(nodes)

    def test_merge_nodes_batch_requires_label(self):
        """Test that each node must have a label."""
        builder = AdminQueryBuilder()
        nodes = [{"properties": {"name": "APT28"}}]

        with pytest.raises(QueryValidationError) as exc_info:
            builder.merge_nodes_batch(nodes)

        assert "must have a 'label' field" in str(exc_info.value)

    def test_merge_nodes_batch_requires_properties(self):
        """Test that each node must have properties."""
        builder = AdminQueryBuilder()
        nodes = [{"label": "ThreatActor"}]

        with pytest.raises(QueryValidationError) as exc_info:
            builder.merge_nodes_batch(nodes)

        assert "must have a 'properties' field" in str(exc_info.value)

    def test_merge_nodes_batch_requires_match_property_in_properties(self):
        """Test that match property must exist in node properties."""
        builder = AdminQueryBuilder()
        nodes = [{"label": "ThreatActor", "properties": {"type": "Nation-State"}}]

        with pytest.raises(QueryValidationError) as exc_info:
            builder.merge_nodes_batch(nodes, match_property="name")

        assert "must have 'name' in properties" in str(exc_info.value)

    def test_merge_nodes_batch_empty_list(self):
        """Test batch merge with empty list."""
        builder = AdminQueryBuilder()
        query, params = builder.merge_nodes_batch([])

        assert "UNWIND $nodes" in query
        assert params["nodes"] == []


class TestAdminDeleteNode:
    """Test suite for delete_node method."""

    def test_delete_node_basic(self):
        """Test basic node deletion."""
        builder = AdminQueryBuilder()
        query, params = builder.delete_node("ThreatActor", "name", "APT28")

        assert "MATCH (n:ThreatActor {name: $value})" in query
        assert "DETACH DELETE n" in query
        assert params["value"] == "APT28"

    def test_delete_node_validates_label(self):
        """Test that delete_node validates labels."""
        builder = AdminQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.delete_node("InvalidLabel", "name", "test")

    def test_delete_node_validates_property(self):
        """Test that delete_node validates properties."""
        builder = AdminQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.delete_node("ThreatActor", "invalid_prop", "test")


class TestAdminMergeRelationship:
    """Test suite for merge_relationship method."""

    def test_merge_relationship_basic(self):
        """Test basic relationship merge without properties."""
        builder = AdminQueryBuilder()
        query, params = builder.merge_relationship(
            "ThreatActor", "APT28", "Malware", "X-Agent", "USES"
        )

        assert "MATCH (from:ThreatActor {name: $from_value})" in query
        assert "MATCH (to:Malware {name: $to_value})" in query
        assert "MERGE (from)-[r:USES]->(to)" in query
        assert params["from_value"] == "APT28"
        assert params["to_value"] == "X-Agent"
        assert "properties" not in params

    def test_merge_relationship_with_properties(self):
        """Test relationship merge with properties."""
        builder = AdminQueryBuilder()
        query, params = builder.merge_relationship(
            "ThreatActor",
            "APT28",
            "Malware",
            "X-Agent",
            "USES",
            {"source": "Report XYZ", "first_seen": "2015-06-01"},
        )

        assert "MERGE (from)-[r:USES]->(to)" in query
        assert "SET r += $properties" in query
        assert params["properties"] == {
            "source": "Report XYZ",
            "first_seen": "2015-06-01",
        }

    def test_merge_relationship_custom_match_property(self):
        """Test relationship merge with custom match property."""
        builder = AdminQueryBuilder()
        query, params = builder.merge_relationship(
            "Vulnerability",
            "CVE-2024-1234",
            "Observable",
            "malicious.exe",
            "RELATED_TO",
            match_property="cve_id",
        )

        assert "{cve_id: $from_value}" in query

    def test_merge_relationship_validates_labels(self):
        """Test that merge_relationship validates labels."""
        builder = AdminQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.merge_relationship(
                "InvalidLabel", "test", "Malware", "X-Agent", "USES"
            )

    def test_merge_relationship_validates_relationship_type(self):
        """Test that merge_relationship validates relationship types."""
        builder = AdminQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.merge_relationship(
                "ThreatActor", "APT28", "Malware", "X-Agent", "INVALID_REL"
            )

    def test_merge_relationship_validates_properties(self):
        """Test that merge_relationship validates properties."""
        builder = AdminQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.merge_relationship(
                "ThreatActor",
                "APT28",
                "Malware",
                "X-Agent",
                "USES",
                {"invalid_prop": "test"},
            )

    def test_merge_relationship_validates_match_property(self):
        """Test that merge_relationship validates match property."""
        builder = AdminQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.merge_relationship(
                "ThreatActor",
                "APT28",
                "Malware",
                "X-Agent",
                "USES",
                match_property="invalid_prop",
            )


class TestAdminMergeRelationshipsBatch:
    """Test suite for merge_relationships_batch method."""

    def test_merge_relationships_batch_basic(self):
        """Test basic batch relationship merge."""
        builder = AdminQueryBuilder()
        relationships = [
            {
                "from_label": "ThreatActor",
                "from_value": "APT28",
                "to_label": "Malware",
                "to_value": "X-Agent",
                "type": "USES",
                "properties": {"source": "Report 1"},
            }
        ]

        query, params = builder.merge_relationships_batch(relationships)

        assert "UNWIND $relationships AS relData" in query
        assert "MATCH (from:$(relData.from_label) {name: relData.from_value})" in query
        assert "MATCH (to:$(relData.to_label) {name: relData.to_value})" in query
        assert "MERGE (from)-[r:$(relData.type)]->(to)" in query
        assert "SET r +=" in query
        assert params["relationships"] == relationships

    def test_merge_relationships_batch_without_properties(self):
        """Test batch merge without relationship properties."""
        builder = AdminQueryBuilder()
        relationships = [
            {
                "from_label": "ThreatActor",
                "from_value": "APT28",
                "to_label": "Malware",
                "to_value": "X-Agent",
                "type": "USES",
            }
        ]

        query, params = builder.merge_relationships_batch(relationships)

        assert "MERGE (from)-[r:$(relData.type)]->(to)" in query
        assert "CASE WHEN relData.properties IS NOT NULL" in query

    def test_merge_relationships_batch_custom_match_property(self):
        """Test batch merge with custom match property."""
        builder = AdminQueryBuilder()
        relationships = [
            {
                "from_label": "Vulnerability",
                "from_value": "CVE-2024-1234",
                "to_label": "Observable",
                "to_value": "malicious.exe",
                "type": "RELATED_TO",
            }
        ]

        query, params = builder.merge_relationships_batch(
            relationships, match_property="cve_id"
        )

        assert "{cve_id: relData.from_value}" in query

    def test_merge_relationships_batch_validates_required_fields(self):
        """Test that all required fields must be present."""
        builder = AdminQueryBuilder()

        # Missing 'type'
        relationships = [
            {
                "from_label": "ThreatActor",
                "from_value": "APT28",
                "to_label": "Malware",
                "to_value": "X-Agent",
            }
        ]

        with pytest.raises(QueryValidationError) as exc_info:
            builder.merge_relationships_batch(relationships)

        assert "must have" in str(exc_info.value)

    def test_merge_relationships_batch_validates_labels(self):
        """Test that batch merge validates all labels."""
        builder = AdminQueryBuilder()
        relationships = [
            {
                "from_label": "InvalidLabel",
                "from_value": "test",
                "to_label": "Malware",
                "to_value": "X-Agent",
                "type": "USES",
            }
        ]

        with pytest.raises(QueryValidationError):
            builder.merge_relationships_batch(relationships)

    def test_merge_relationships_batch_validates_relationship_types(self):
        """Test that batch merge validates relationship types."""
        builder = AdminQueryBuilder()
        relationships = [
            {
                "from_label": "ThreatActor",
                "from_value": "APT28",
                "to_label": "Malware",
                "to_value": "X-Agent",
                "type": "INVALID_REL",
            }
        ]

        with pytest.raises(QueryValidationError):
            builder.merge_relationships_batch(relationships)

    def test_merge_relationships_batch_validates_properties(self):
        """Test that batch merge validates relationship properties."""
        builder = AdminQueryBuilder()
        relationships = [
            {
                "from_label": "ThreatActor",
                "from_value": "APT28",
                "to_label": "Malware",
                "to_value": "X-Agent",
                "type": "USES",
                "properties": {"invalid_prop": "test"},
            }
        ]

        with pytest.raises(QueryValidationError):
            builder.merge_relationships_batch(relationships)

    def test_merge_relationships_batch_empty_list(self):
        """Test batch merge with empty list."""
        builder = AdminQueryBuilder()
        query, params = builder.merge_relationships_batch([])

        assert "UNWIND $relationships" in query
        assert params["relationships"] == []


class TestAdminDeleteRelationship:
    """Test suite for delete_relationship method."""

    def test_delete_relationship_specific_type(self):
        """Test deleting specific relationship type."""
        builder = AdminQueryBuilder()
        query, params = builder.delete_relationship(
            "ThreatActor", "APT28", "Malware", "X-Agent", "USES"
        )

        assert "MATCH (from:ThreatActor {name: $from_value})" in query
        assert "-[r:USES]->" in query
        assert "(to:Malware {name: $to_value})" in query
        assert "DELETE r" in query
        assert params["from_value"] == "APT28"
        assert params["to_value"] == "X-Agent"

    def test_delete_relationship_all_types(self):
        """Test deleting all relationships between nodes."""
        builder = AdminQueryBuilder()
        query, params = builder.delete_relationship(
            "ThreatActor", "APT28", "Malware", "X-Agent"
        )

        assert "-[r]->" in query
        assert "DELETE r" in query

    def test_delete_relationship_custom_match_property(self):
        """Test delete with custom match property."""
        builder = AdminQueryBuilder()
        query, params = builder.delete_relationship(
            "Vulnerability",
            "CVE-2024-1234",
            "Observable",
            "malicious.exe",
            match_property="cve_id",
        )

        assert "{cve_id: $from_value}" in query

    def test_delete_relationship_validates_labels(self):
        """Test that delete_relationship validates labels."""
        builder = AdminQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.delete_relationship("InvalidLabel", "test", "Malware", "X-Agent")

    def test_delete_relationship_validates_relationship_type(self):
        """Test that delete_relationship validates relationship types."""
        builder = AdminQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.delete_relationship(
                "ThreatActor", "APT28", "Malware", "X-Agent", "INVALID_REL"
            )

    def test_delete_relationship_validates_match_property(self):
        """Test that delete_relationship validates match property."""
        builder = AdminQueryBuilder()
        with pytest.raises(QueryValidationError):
            builder.delete_relationship(
                "ThreatActor",
                "APT28",
                "Malware",
                "X-Agent",
                match_property="invalid_prop",
            )


class TestAdminParameterization:
    """Test suite for proper parameterization in AdminQueryBuilder."""

    def test_merge_node_parameterizes_values(self):
        """Test that merge_node parameterizes all values."""
        builder = AdminQueryBuilder()
        malicious_value = "'; DELETE (n); //"

        query, params = builder.merge_node("ThreatActor", {"name": malicious_value})

        # Malicious value should be in params, not in query
        assert malicious_value not in query
        assert params["match_name"] == malicious_value

    def test_merge_nodes_batch_parameterizes_values(self):
        """Test that batch operations parameterize values."""
        builder = AdminQueryBuilder()
        malicious_value = "'; DROP DATABASE; //"

        nodes = [{"label": "ThreatActor", "properties": {"name": malicious_value}}]

        query, params = builder.merge_nodes_batch(nodes)

        # Malicious value should only be in params
        assert malicious_value not in query
        assert params["nodes"][0]["properties"]["name"] == malicious_value

    def test_merge_relationship_parameterizes_values(self):
        """Test that merge_relationship parameterizes values."""
        builder = AdminQueryBuilder()
        malicious_value = "admin' OR 1=1 --"

        query, params = builder.merge_relationship(
            "ThreatActor", malicious_value, "Malware", "X-Agent", "USES"
        )

        # Malicious value should be in params, not in query
        assert malicious_value not in query
        assert params["from_value"] == malicious_value


class TestAdminValidatePropertiesDict:
    """Test suite for _validate_properties_dict helper method."""

    def test_validates_all_properties_in_dict(self):
        """Test that all properties in dict are validated."""
        builder = AdminQueryBuilder()

        valid_props = {"name": "APT28", "type": "Nation-State"}
        result = builder._validate_properties_dict(valid_props)
        assert result == valid_props

    def test_rejects_invalid_properties_in_dict(self):
        """Test that invalid properties are rejected."""
        builder = AdminQueryBuilder()

        invalid_props = {"name": "APT28", "invalid_prop": "test"}
        with pytest.raises(QueryValidationError):
            builder._validate_properties_dict(invalid_props)

    def test_accepts_empty_dict(self):
        """Test that empty dict is accepted."""
        builder = AdminQueryBuilder()
        result = builder._validate_properties_dict({})
        assert result == {}

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
        """Test basic batch merge with multiple labels."""
        builder = AdminQueryBuilder()
        nodes = [
            {
                "label": "ThreatActor",
                "properties": {"name": "APT28", "type": "Nation-State"},
            },
            {"label": "Malware", "properties": {"name": "X-Agent", "family": "Sofacy"}},
            {
                "label": "ThreatActor",
                "properties": {"name": "APT29", "type": "Nation-State"},
            },
        ]

        queries = builder.merge_nodes_batch(nodes)

        # Should return a list of queries
        assert isinstance(queries, list)
        assert len(queries) == 2  # One for ThreatActor, one for Malware

        # Check ThreatActor query
        threat_actor_query = None
        malware_query = None

        for query, params in queries:
            if "nodes_ThreatActor" in query:
                threat_actor_query = (query, params)
            elif "nodes_Malware" in query:
                malware_query = (query, params)

        # Verify ThreatActor query
        assert threat_actor_query is not None
        query, params = threat_actor_query
        assert "UNWIND $nodes_ThreatActor AS props" in query
        assert "MERGE (n:ThreatActor {name: props.name})" in query
        assert "SET n += props" in query
        assert "RETURN count(n) AS count" in query
        assert "'ThreatActor' AS label" in query
        assert len(params["nodes_ThreatActor"]) == 2  # Two ThreatActor nodes

        # Verify Malware query
        assert malware_query is not None
        query, params = malware_query
        assert "UNWIND $nodes_Malware AS props" in query
        assert "MERGE (n:Malware {name: props.name})" in query
        assert len(params["nodes_Malware"]) == 1  # One Malware node

    def test_merge_nodes_batch_custom_match_property(self):
        """Test batch merge with custom match property."""
        builder = AdminQueryBuilder()
        nodes = [
            {"label": "Tool", "properties": {"name": "Nmap", "version": "7.91"}},
        ]

        queries = builder.merge_nodes_batch(nodes, match_property="version")

        assert len(queries) == 1
        query, params = queries[0]

        assert "MERGE (n:Tool {version: props.version})" in query
        assert "name" in params["nodes_Tool"][0]
        assert "version" in params["nodes_Tool"][0]

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

    def test_merge_nodes_batch_empty_list(self):
        """Test batch merge with empty list returns empty list."""
        builder = AdminQueryBuilder()
        nodes = []

        queries = builder.merge_nodes_batch(nodes)

        assert queries == []
        assert len(queries) == 0

    def test_merge_nodes_batch_missing_label(self):
        """Test that nodes without label field raise error."""
        builder = AdminQueryBuilder()
        nodes = [
            {"properties": {"name": "Test"}},  # Missing 'label'
        ]

        with pytest.raises(QueryValidationError) as exc_info:
            builder.merge_nodes_batch(nodes)

        assert "must have a 'label' field" in str(exc_info.value)

    def test_merge_nodes_batch_missing_properties(self):
        """Test that nodes without properties field raise error."""
        builder = AdminQueryBuilder()
        nodes = [
            {"label": "ThreatActor"},  # Missing 'properties'
        ]

        with pytest.raises(QueryValidationError) as exc_info:
            builder.merge_nodes_batch(nodes)

        assert "must have a 'properties' field" in str(exc_info.value)

    def test_merge_nodes_batch_invalid_label(self):
        """Test that invalid labels are rejected."""
        builder = AdminQueryBuilder()
        nodes = [
            {"label": "InvalidLabel", "properties": {"name": "Test"}},
        ]

        with pytest.raises(QueryValidationError) as exc_info:
            builder.merge_nodes_batch(nodes)

        assert "not allowed" in str(exc_info.value)

    def test_merge_nodes_batch_missing_match_property(self):
        """Test that nodes missing the match property raise error."""
        builder = AdminQueryBuilder()
        nodes = [
            {
                "label": "ThreatActor",
                "properties": {"type": "Nation-State"},
            },  # Missing 'name'
        ]

        with pytest.raises(QueryValidationError) as exc_info:
            builder.merge_nodes_batch(nodes)

        assert "must have 'name' in properties" in str(exc_info.value)

    def test_merge_nodes_batch_invalid_property(self):
        """Test that invalid properties are rejected."""
        builder = AdminQueryBuilder()
        nodes = [
            {
                "label": "ThreatActor",
                "properties": {"name": "APT28", "invalid_prop": "value"},
            },
        ]

        with pytest.raises(QueryValidationError) as exc_info:
            builder.merge_nodes_batch(nodes)

        assert "not allowed" in str(exc_info.value)

    def test_merge_nodes_batch_groups_by_label(self):
        """Test that nodes are correctly grouped by label."""
        builder = AdminQueryBuilder()
        nodes = [
            {"label": "ThreatActor", "properties": {"name": "APT1"}},
            {"label": "Malware", "properties": {"name": "Malware1"}},
            {"label": "ThreatActor", "properties": {"name": "APT2"}},
            {"label": "Tool", "properties": {"name": "Tool1"}},
            {"label": "Malware", "properties": {"name": "Malware2"}},
        ]

        queries = builder.merge_nodes_batch(nodes)

        # Should create 3 queries (ThreatActor, Malware, Tool)
        assert len(queries) == 3

        # Count nodes per label
        label_counts = {}
        for query, params in queries:
            for label in ["ThreatActor", "Malware", "Tool"]:
                param_key = f"nodes_{label}"
                if param_key in params:
                    label_counts[label] = len(params[param_key])

        assert label_counts["ThreatActor"] == 2
        assert label_counts["Malware"] == 2
        assert label_counts["Tool"] == 1


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
        """Test basic batch merge with multiple relationship patterns."""
        builder = AdminQueryBuilder()
        relationships = [
            {
                "from_label": "ThreatActor",
                "from_value": "APT28",
                "to_label": "Malware",
                "to_value": "X-Agent",
                "type": "USES",
                "properties": {"source": "Report 1"},
            },
            {
                "from_label": "ThreatActor",
                "from_value": "APT29",
                "to_label": "Malware",
                "to_value": "Y-Agent",
                "type": "USES",
                "properties": {"source": "Report 2"},
            },
        ]

        queries = builder.merge_relationships_batch(relationships)

        # Should return a list of queries
        assert isinstance(queries, list)
        assert len(queries) == 1  # Same pattern (ThreatActor)-[USES]->(Malware)

        query, params = queries[0]

        # Verify query structure
        assert "UNWIND $rels_ThreatActor_USES_Malware AS relData" in query
        assert "MATCH (from:ThreatActor {name: relData.from_value})" in query
        assert "MATCH (to:Malware {name: relData.to_value})" in query
        assert "MERGE (from)-[r:USES]->(to)" in query
        assert "SET r += relData.properties" in query
        assert "RETURN count(r) AS count" in query

        # Verify parameters
        assert "rels_ThreatActor_USES_Malware" in params
        assert len(params["rels_ThreatActor_USES_Malware"]) == 2

    def test_merge_relationships_batch_multiple_patterns(self):
        """Test batch merge with different relationship patterns."""
        builder = AdminQueryBuilder()
        relationships = [
            {
                "from_label": "ThreatActor",
                "from_value": "APT28",
                "to_label": "Malware",
                "to_value": "X-Agent",
                "type": "USES",
            },
            {
                "from_label": "Campaign",
                "from_value": "Operation X",
                "to_label": "ThreatActor",
                "to_value": "APT28",
                "type": "LAUNCHED",
            },
        ]

        queries = builder.merge_relationships_batch(relationships)

        # Should create 2 queries (different patterns)
        assert len(queries) == 2

        # Verify both patterns exist
        patterns = []
        for query, params in queries:
            if "USES" in query:
                patterns.append("USES")
            if "LAUNCHED" in query:
                patterns.append("LAUNCHED")

        assert "USES" in patterns
        assert "LAUNCHED" in patterns

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
            },
        ]

        queries = builder.merge_relationships_batch(relationships)

        assert len(queries) == 1
        query, params = queries[0]

        # Should still have SET clause but with empty properties
        assert "SET r += relData.properties" in query
        assert params["rels_ThreatActor_USES_Malware"][0]["properties"] == {}

    def test_merge_relationships_batch_custom_match_property(self):
        """Test batch merge with custom match property."""
        builder = AdminQueryBuilder()
        relationships = [
            {
                "from_label": "ThreatActor",
                "from_value": "id-123",
                "to_label": "Malware",
                "to_value": "id-456",
                "type": "USES",
            },
        ]

        queries = builder.merge_relationships_batch(relationships, match_property="id")

        assert len(queries) == 1
        query, params = queries[0]

        assert "MATCH (from:ThreatActor {id: relData.from_value})" in query
        assert "MATCH (to:Malware {id: relData.to_value})" in query

    def test_merge_relationships_batch_empty_list(self):
        """Test batch merge with empty list returns empty list."""
        builder = AdminQueryBuilder()
        relationships = []

        queries = builder.merge_relationships_batch(relationships)

        assert queries == []
        assert len(queries) == 0

    def test_merge_relationships_batch_missing_required_fields(self):
        """Test that relationships missing required fields raise error."""
        builder = AdminQueryBuilder()
        relationships = [
            {
                "from_label": "ThreatActor",
                "from_value": "APT28",
                "to_label": "Malware",
                # Missing 'to_value' and 'type'
            },
        ]

        with pytest.raises(QueryValidationError) as exc_info:
            builder.merge_relationships_batch(relationships)

        assert "must have:" in str(exc_info.value)

    def test_merge_relationships_batch_invalid_labels(self):
        """Test that invalid labels are rejected."""
        builder = AdminQueryBuilder()
        relationships = [
            {
                "from_label": "InvalidLabel",
                "from_value": "Test",
                "to_label": "Malware",
                "to_value": "X-Agent",
                "type": "USES",
            },
        ]

        with pytest.raises(QueryValidationError):
            builder.merge_relationships_batch(relationships)

    def test_merge_relationships_batch_invalid_relationship_type(self):
        """Test that invalid relationship types are rejected."""
        builder = AdminQueryBuilder()
        relationships = [
            {
                "from_label": "ThreatActor",
                "from_value": "APT28",
                "to_label": "Malware",
                "to_value": "X-Agent",
                "type": "INVALID_REL",
            },
        ]

        with pytest.raises(QueryValidationError):
            builder.merge_relationships_batch(relationships)

    def test_merge_relationships_batch_groups_by_pattern(self):
        """Test that relationships are correctly grouped by pattern."""
        builder = AdminQueryBuilder()
        relationships = [
            # Pattern 1: (ThreatActor)-[USES]->(Malware)
            {
                "from_label": "ThreatActor",
                "from_value": "APT1",
                "to_label": "Malware",
                "to_value": "M1",
                "type": "USES",
            },
            {
                "from_label": "ThreatActor",
                "from_value": "APT2",
                "to_label": "Malware",
                "to_value": "M2",
                "type": "USES",
            },
            # Pattern 2: (ThreatActor)-[TARGETS]->(Organization)
            {
                "from_label": "ThreatActor",
                "from_value": "APT1",
                "to_label": "Organization",
                "to_value": "O1",
                "type": "TARGETS",
            },
            # Pattern 3: (Campaign)-[USES]->(Malware)
            {
                "from_label": "Campaign",
                "from_value": "C1",
                "to_label": "Malware",
                "to_value": "M1",
                "type": "USES",
            },
        ]

        queries = builder.merge_relationships_batch(relationships)

        # Should create 3 queries (3 unique patterns)
        assert len(queries) == 3

        # Count relationships per pattern
        pattern_counts = {}
        for query, params in queries:
            for key, value in params.items():
                pattern_counts[key] = len(value)

        # Pattern 1 should have 2 relationships
        assert pattern_counts.get("rels_ThreatActor_USES_Malware") == 2
        # Patterns 2 and 3 should have 1 each
        assert pattern_counts.get("rels_ThreatActor_TARGETS_Organization") == 1
        assert pattern_counts.get("rels_Campaign_USES_Malware") == 1


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
    """Test suite for proper parameterization in Admin methods."""

    def test_merge_nodes_batch_parameterizes_values(self):
        """Test that node property values are parameterized."""
        builder = AdminQueryBuilder()

        # Try with potentially malicious values
        malicious_name = "'; DROP TABLE nodes; --"
        nodes = [
            {
                "label": "ThreatActor",
                "properties": {"name": malicious_name, "type": "Test"},
            },
        ]

        queries = builder.merge_nodes_batch(nodes)

        assert len(queries) == 1
        query, params = queries[0]

        # Malicious string should be in params, not in query
        assert malicious_name not in query
        assert params["nodes_ThreatActor"][0]["name"] == malicious_name

    def test_merge_relationships_batch_parameterizes_values(self):
        """Test that relationship values are parameterized."""
        builder = AdminQueryBuilder()

        malicious_value = "Test'; DELETE (n); //"
        relationships = [
            {
                "from_label": "ThreatActor",
                "from_value": malicious_value,
                "to_label": "Malware",
                "to_value": "Test",
                "type": "USES",
            },
        ]

        queries = builder.merge_relationships_batch(relationships)

        assert len(queries) == 1
        query, params = queries[0]

        # Malicious string should be in params, not in query
        assert malicious_value not in query
        assert (
            params["rels_ThreatActor_USES_Malware"][0]["from_value"] == malicious_value
        )


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


class TestSearchNodesWithMetadata:
    """Test suite for enhanced search_nodes method with metadata support."""

    def test_search_with_metadata_enabled(self):
        """Test that metadata is included when requested."""
        builder = SafeQueryBuilder()
        query, params = builder.search_nodes(
            search_value="Shadow", match_type="starts_with", include_metadata=True
        )

        assert "labels(n)[0] AS label" in query
        assert "elementId(n) AS id" in query
        assert "n.name AS name" in query
        assert params["search_value"] == "Shadow"

    def test_search_without_metadata(self):
        """Test that metadata is excluded when not requested."""
        builder = SafeQueryBuilder()
        query, params = builder.search_nodes(
            search_value="Shadow", match_type="starts_with", include_metadata=False
        )

        assert "labels(n)[0]" not in query
        assert "elementId(n)" not in query
        assert "RETURN n" in query

    def test_search_with_label_filter(self):
        """Test search with specific label filter."""
        builder = SafeQueryBuilder()
        query, params = builder.search_nodes(
            label="ThreatActor",
            search_value="APT",
            match_type="starts_with",
            include_metadata=True,
        )

        assert ":ThreatActor" in query
        assert "WHERE n.name IS NOT NULL" in query

    def test_search_without_label_filter(self):
        """Test search across all labels."""
        builder = SafeQueryBuilder()
        query, params = builder.search_nodes(
            search_value="test", match_type="contains", include_metadata=True
        )

        assert "MATCH (n)" in query
        assert ":ThreatActor" not in query

    def test_exact_match_type(self):
        """Test exact match type uses equality."""
        builder = SafeQueryBuilder()
        query, params = builder.search_nodes(search_value="APT28", match_type="exact")

        assert "n.name = $search_value" in query
        assert "STARTS WITH" not in query
        assert "CONTAINS" not in query

    def test_starts_with_match_type(self):
        """Test starts_with match type uses STARTS WITH."""
        builder = SafeQueryBuilder()
        query, params = builder.search_nodes(
            search_value="APT", match_type="starts_with"
        )

        assert "STARTS WITH" in query
        assert "toLower" in query

    def test_contains_match_type(self):
        """Test contains match type uses CONTAINS."""
        builder = SafeQueryBuilder()
        query, params = builder.search_nodes(
            search_value="shadow", match_type="contains"
        )

        assert "CONTAINS" in query
        assert "toLower" in query

    def test_invalid_match_type_raises_error(self):
        """Test that invalid match type raises error."""
        builder = SafeQueryBuilder()

        with pytest.raises(QueryValidationError) as exc_info:
            builder.search_nodes(search_value="test", match_type="invalid")

        assert "Invalid match_type" in str(exc_info.value)

    def test_custom_search_property(self):
        """Test searching on non-name property."""
        builder = SafeQueryBuilder()
        query, params = builder.search_nodes(
            search_property="description", search_value="malware", match_type="contains"
        )

        assert "n.description" in query
        assert "ORDER BY n.description" in query

    def test_custom_limit(self):
        """Test custom limit is applied."""
        builder = SafeQueryBuilder()
        query, params = builder.search_nodes(search_value="test", limit=50)

        assert params["limit"] == 50

    def test_parameterization(self):
        """Test that search value is properly parameterized."""
        builder = SafeQueryBuilder()
        query, params = builder.search_nodes(
            search_value="'; DROP TABLE nodes; --", match_type="exact"
        )

        assert "$search_value" in query
        assert "DROP TABLE" not in query
        assert params["search_value"] == "'; DROP TABLE nodes; --"


class TestFuzzySearchNodes:
    """Test suite for fuzzy_search_nodes method with relevance scoring."""

    def test_fuzzy_search_includes_relevance(self):
        """Test that relevance scoring is included."""
        builder = SafeQueryBuilder()
        query, params = builder.fuzzy_search_nodes(search_value="shadow")

        assert "relevance" in query.lower()
        assert "CASE" in query
        assert "STARTS WITH" in query

    def test_fuzzy_search_with_metadata(self):
        """Test fuzzy search returns metadata by default."""
        builder = SafeQueryBuilder()
        query, params = builder.fuzzy_search_nodes(search_value="APT")

        assert "labels(n)[0] AS label" in query
        assert "elementId(n) AS id" in query

    def test_fuzzy_search_orders_by_relevance(self):
        """Test that results are ordered by relevance first."""
        builder = SafeQueryBuilder()
        query, params = builder.fuzzy_search_nodes(search_value="test")

        assert "ORDER BY relevance" in query

    def test_fuzzy_search_with_label(self):
        """Test fuzzy search with label filter."""
        builder = SafeQueryBuilder()
        query, params = builder.fuzzy_search_nodes(
            label="Malware", search_value="crypto"
        )

        assert ":Malware" in query
        assert "CONTAINS" in query

    def test_fuzzy_search_without_metadata(self):
        """Test fuzzy search without metadata."""
        builder = SafeQueryBuilder()
        query, params = builder.fuzzy_search_nodes(
            search_value="test", include_metadata=False
        )

        assert "RETURN n" in query
        assert "labels(n)[0] AS label" not in query

    def test_relevance_scoring_logic(self):
        """Test relevance scoring distinguishes prefix vs contains."""
        builder = SafeQueryBuilder()
        query, params = builder.fuzzy_search_nodes(search_value="shadow")

        assert "WHEN toLower(n.name) STARTS WITH toLower($search_value) THEN 1" in query
        assert "ELSE 2" in query


class TestCheckNodeExists:
    """Test suite for check_node_exists method."""

    def test_check_exists_returns_count_and_boolean(self):
        """Test that query returns both count and exists boolean."""
        builder = SafeQueryBuilder()
        query, params = builder.check_node_exists(
            property_name="name", property_value="APT28"
        )

        assert "count(n) AS count" in query
        assert "count(n) > 0 AS exists" in query

    def test_check_exists_with_label(self):
        """Test existence check with specific label."""
        builder = SafeQueryBuilder()
        query, params = builder.check_node_exists(
            property_name="name", property_value="APT28", label="ThreatActor"
        )

        assert ":ThreatActor" in query
        assert params["value"] == "APT28"

    def test_check_exists_without_label(self):
        """Test existence check across all labels."""
        builder = SafeQueryBuilder()
        query, params = builder.check_node_exists(
            property_name="name", property_value="test"
        )

        assert "MATCH (n {name: $value})" in query

    def test_check_exists_custom_property(self):
        """Test existence check on non-name property."""
        builder = SafeQueryBuilder()
        query, params = builder.check_node_exists(
            property_name="cve_id", property_value="CVE-2024-1234"
        )

        assert "n.cve_id" in query

    def test_check_exists_parameterization(self):
        """Test that value is properly parameterized."""
        builder = SafeQueryBuilder()
        query, params = builder.check_node_exists(
            property_name="name", property_value="malicious'; DROP TABLE"
        )

        assert "$value" in query
        assert "DROP TABLE" not in query


class TestGetAllNodeNames:
    """Test suite for get_all_node_names method."""

    def test_get_all_names_with_metadata(self):
        """Test getting all names with metadata."""
        builder = SafeQueryBuilder()
        query, params = builder.get_all_node_names(include_metadata=True)

        assert "DISTINCT n.name AS name" in query
        assert "labels(n)[0] AS label" in query

    def test_get_all_names_without_metadata(self):
        """Test getting all names without metadata."""
        builder = SafeQueryBuilder()
        query, params = builder.get_all_node_names(include_metadata=False)

        assert "DISTINCT n.name AS name" in query
        assert "labels(n)[0]" not in query

    def test_get_all_names_with_label_filter(self):
        """Test getting names for specific label."""
        builder = SafeQueryBuilder()
        query, params = builder.get_all_node_names(label="ThreatActor", limit=500)

        assert ":ThreatActor" in query
        assert params["limit"] == 500

    def test_get_all_names_ordered(self):
        """Test that names are ordered."""
        builder = SafeQueryBuilder()
        query, params = builder.get_all_node_names()

        assert "ORDER BY n.name" in query

    def test_get_all_names_distinct(self):
        """Test that DISTINCT is used to avoid duplicates."""
        builder = SafeQueryBuilder()
        query, params = builder.get_all_node_names()

        assert "DISTINCT" in query

    def test_get_all_names_custom_property(self):
        """Test getting all values of custom property."""
        builder = SafeQueryBuilder()
        query, params = builder.get_all_node_names(property_name="title")

        assert "n.title AS title" in query
        assert "ORDER BY n.title" in query


class TestGetNodeWithRelationshipsEnhanced:
    """Test suite for enhanced get_node_with_relationships method."""

    def test_get_node_with_metadata(self):
        """Test that metadata is included by default."""
        builder = SafeQueryBuilder()
        query, params = builder.get_node_with_relationships(
            property_name="name", property_value="APT28", label="ThreatActor"
        )

        assert "labels(n)[0] AS nodeLabel" in query
        assert "elementId(n) AS nodeId" in query
        assert "labels(connected)[0]" in query

    def test_get_node_without_label(self):
        """Test searching across all labels."""
        builder = SafeQueryBuilder()
        query, params = builder.get_node_with_relationships(
            property_name="name", property_value="test"
        )

        assert "MATCH (n {name: $value})" in query
        assert "WHERE n.name IS NOT NULL" in query

    def test_get_node_with_specific_label(self):
        """Test searching with specific label."""
        builder = SafeQueryBuilder()
        query, params = builder.get_node_with_relationships(
            property_name="name", property_value="APT28", label="ThreatActor"
        )

        assert "MATCH (n:ThreatActor {name: $value})" in query

    def test_get_node_with_relationship_filter(self):
        """Test filtering by relationship type."""
        builder = SafeQueryBuilder()
        query, params = builder.get_node_with_relationships(
            property_name="name", property_value="APT28", relationship_type="USES"
        )

        assert "[r:USES]" in query

    def test_get_node_without_metadata(self):
        """Test getting node without metadata."""
        builder = SafeQueryBuilder()
        query, params = builder.get_node_with_relationships(
            property_name="name", property_value="test", include_metadata=False
        )

        assert "labels(n)[0]" not in query
        assert "elementId(n)" not in query

    def test_get_node_includes_direction(self):
        """Test that relationship direction is included."""
        builder = SafeQueryBuilder()
        query, params = builder.get_node_with_relationships(
            property_name="name", property_value="test"
        )

        assert "direction" in query
        assert "CASE" in query
        assert "startNode(r)" in query

    def test_get_node_uses_optional_match(self):
        """Test that OPTIONAL MATCH is used for relationships."""
        builder = SafeQueryBuilder()
        query, params = builder.get_node_with_relationships(
            property_name="name", property_value="test"
        )

        assert "OPTIONAL MATCH" in query

    def test_get_node_custom_limit(self):
        """Test custom limit for relationships."""
        builder = SafeQueryBuilder()
        query, params = builder.get_node_with_relationships(
            property_name="name", property_value="test", limit=10
        )

        assert params["limit"] == 10

"""Unit tests for the SafeQueryBuilder class.

This module tests the query builder's ability to create safe,
parameterized Cypher queries and prevent injection attacks.
"""

import pytest
from src.services.query_builder import SafeQueryBuilder, QueryValidationError


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

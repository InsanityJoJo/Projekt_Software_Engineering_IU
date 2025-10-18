"""Safe Cypher query builder to prevent injection attacks.

This module provides a safe interface for building Cypher queries from
user input. It uses parameterized queries and validates all inputs to
prevent Cypher injection attacks and restrict operations to read-only.
"""

from typing import Dict, List, Optional, Any
from enum import Enum


class QueryType(Enum):
    """Enumeration of allowed query types."""

    READ = "read"
    # Future: Add WRITE, UPDATE, DELETE with proper authorization


class QueryValidationError(Exception):
    """Raised when query validation fails."""

    pass


class SafeQueryBuilder:
    """Builder for constructing safe, parameterized Cypher queries.

    This class ensures that:
    1. Only read operations are allowed (no DELETE, REMOVE, SET, CREATE)
    2. All user inputs are parameterized (prevents injection)
    3. Labels and property names are validated (whitelist approach)
    4. Query complexity is limited (prevents resource exhaustion)
    """

    # Whitelist of allowed node labels
    ALLOWED_LABELS = {
        "AttackPattern",
        "Campaign",
        "Identity",
        "Incident",
        "Indicator",
        "Malware",
        "Observable",
        "File",
        "DomainName",
        "URL",
        "EmailAddr",
        "IPv4Adress",
        "Organization",
        "Report",
        "ThreatActor",
        "Tool",
        "Vulnerability",
        # Add more labels here
    }

    # Whitelist of allowed relationship types
    ALLOWED_RELATIONSHIPS = {
        "BASED_ON",
        "DETECTS",
        "DESCRIBES",
        "EMPLOYES",
        "HAS_IDENTITY",
        "INDICATED_BY",
        "INVOLVES",
        "LAUNCHED",
        "RELATED_TO",
        "TARGETS",
        "USES",
        # Add more relationship types here
    }

    # Whitelist of allowed property names
    ALLOWED_PROPERTIES = {
        "name",
        "description",
        "title",
        "published_date",
        "source",
        "aliases",
        "type",
        "id",
        "motivation",
        "first_seen",
        "last_seen",
        "version",
        "start_date",
        "end_date",
        "cve_id",
        "cvss_score",
        "family",
        "detection_date",
        "resolved_date",
        "sector",
        "region",
        "roles",
        "contact_info",
        "filename",
        "size",
        "hash_md5",
        "hash_sha1",
        "hash_sha256",
        "domain",
        "addressurl",
        # Add more properties here
    }

    # Forbidden keywords (for read-only enforcement)
    FORBIDDEN_KEYWORDS = {
        "DELETE",
        "REMOVE",
        "CREATE",
        "MERGE",
        "SET",
        "DETACH",
        "DROP",
        "FOREACH",
    }

    def __init__(self, max_results: int = 100):
        """Initialize the query builder.

        Args:
            max_results: Maximum number of results to return (safety limit).
        """
        self.max_results = max_results

    def validate_label(self, label: str) -> str:
        """Validate that a node label is allowed.

        Args:
            label: The label to validate.

        Returns:
            str: The validated label.

        Raises:
            QueryValidationError: If label is not allowed.
        """
        if label not in self.ALLOWED_LABELS:
            raise QueryValidationError(
                f"Label '{label}' is not allowed. "
                f"Allowed labels: {', '.join(self.ALLOWED_LABELS)}"
            )
        return label

    def validate_relationship(self, rel_type: str) -> str:
        """Validate that a relationship type is allowed.

        Args:
            rel_type: The relationship type to validate.

        Returns:
            str: The validated relationship type.

        Raises:
            QueryValidationError: If relationship type is not allowed.
        """
        if rel_type not in self.ALLOWED_RELATIONSHIPS:
            raise QueryValidationError(
                f"Relationship '{rel_type}' is not allowed. "
                f"Allowed types: {', '.join(self.ALLOWED_RELATIONSHIPS)}"
            )
        return rel_type

    def validate_property(self, prop: str) -> str:
        """Validate that a property name is allowed.

        Args:
            prop: The property name to validate.

        Returns:
            str: The validated property name.

        Raises:
            QueryValidationError: If property is not allowed.
        """
        if prop not in self.ALLOWED_PROPERTIES:
            raise QueryValidationError(
                f"Property '{prop}' is not allowed. "
                f"Allowed properties: {', '.join(self.ALLOWED_PROPERTIES)}"
            )
        return prop

    def validate_query_safety(self, query: str) -> None:
        """Check that query contains no forbidden operations.

        Args:
            query: The query string to validate.

        Raises:
            QueryValidationError: If query contains forbidden keywords.
        """
        query_upper = query.upper()
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in query_upper:
                raise QueryValidationError(
                    f"Query contains forbidden keyword: {keyword}. "
                    "Only read operations are allowed."
                )

    def find_node_by_property(
        self,
        label: str,
        property_name: str,
        property_value: Any,
        return_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """Build a safe query to find nodes by property.

        Args:
            label: Node label to search.
            property_name: Property to match on.
            property_value: Value to match.
            return_properties: List of properties to return (None = all).
            limit: Maximum results to return.

        Returns:
            tuple: (query_string, parameters_dict)

        Raises:
            QueryValidationError: If validation fails.
        """
        # Validate inputs
        label = self.validate_label(label)
        property_name = self.validate_property(property_name)

        # Build return clause
        if return_properties:
            validated_props = [self.validate_property(p) for p in return_properties]
            return_clause = ", ".join([f"n.{p} AS {p}" for p in validated_props])
        else:
            return_clause = "n"

        # Build query
        query = f"""
        MATCH (n:{label} {{{property_name}: $value}})
        RETURN {return_clause}
        LIMIT $limit
        """

        params = {"value": property_value, "limit": limit or self.max_results}

        self.validate_query_safety(query)
        return query, params

    def find_connected_nodes(
        self,
        start_label: str,
        start_property: str,
        start_value: Any,
        relationship_type: Optional[str] = None,
        max_hops: int = 1,
        limit: Optional[int] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """Build a query to find nodes connected to a starting node.

        Args:
            start_label: Label of the starting node.
            start_property: Property to identify the starting node.
            start_value: Value to match the starting node.
            relationship_type: Optional specific relationship type.
            max_hops: Maximum number of hops (1-3, default: 1).
            limit: Maximum results to return.

        Returns:
            tuple: (query_string, parameters_dict)

        Raises:
            QueryValidationError: If validation fails.
        """
        # Validate inputs
        start_label = self.validate_label(start_label)
        start_property = self.validate_property(start_property)

        # Limit max hops to prevent resource exhaustion
        if max_hops < 1 or max_hops > 3:
            raise QueryValidationError("max_hops must be between 1 and 3")

        # Build relationship pattern
        if relationship_type:
            rel_type = self.validate_relationship(relationship_type)
            rel_pattern = f"[r:{rel_type}*1..{max_hops}]"
        else:
            rel_pattern = f"[r*1..{max_hops}]"

        # Build query
        query = f"""
        MATCH path = (start:{start_label} {{{start_property}: $start_value}})
                     -{rel_pattern}-(connected)
        RETURN start, connected, relationships(path) AS relationships
        LIMIT $limit
        """

        params = {"start_value": start_value, "limit": limit or self.max_results}

        self.validate_query_safety(query)
        return query, params

    def get_node_with_relationships(
        self,
        label: str,
        property_name: str,
        property_value: Any,
        relationship_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """Build a query to get a node and its direct relationships.

        Args:
            label: Node label.
            property_name: Property to identify the node.
            property_value: Value to match.
            relationship_type: Optional specific relationship type filter.
            limit: Maximum relationships to return.

        Returns:
            tuple: (query_string, parameters_dict)
        """
        # Validate inputs
        label = self.validate_label(label)
        property_name = self.validate_property(property_name)

        # Build relationship filter
        if relationship_type:
            rel_type = self.validate_relationship(relationship_type)
            rel_pattern = f"[r:{rel_type}]"
        else:
            rel_pattern = "[r]"

        # Build query
        query = f"""
        MATCH (n:{label} {{{property_name}: $value}})
        OPTIONAL MATCH (n)-{rel_pattern}-(connected)
        RETURN n, 
               collect({{
                   relationship: r,
                   node: connected,
                   type: type(r),
                   direction: CASE 
                     WHEN startNode(r) = n THEN 'outgoing'
                     ELSE 'incoming'
                   END
               }}) AS connections
        LIMIT $limit
        """

        params = {"value": property_value, "limit": limit or self.max_results}

        self.validate_query_safety(query)
        return query, params

    def search_nodes(
        self,
        label: Optional[str] = None,
        search_property: str = "name",
        search_value: str = "",
        match_type: str = "contains",  # 'exact', 'starts_with', 'contains'
        limit: Optional[int] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """Build a safe search query for nodes.

        Args:
            label: Optional node label to filter by.
            search_property: Property to search in.
            search_value: Value to search for.
            match_type: Type of matching ('exact', 'starts_with', 'contains').
            limit: Maximum results to return.

        Returns:
            tuple: (query_string, parameters_dict)
        """
        # Validate inputs
        search_property = self.validate_property(search_property)

        # Build label clause
        if label:
            label = self.validate_label(label)
            label_clause = f":{label}"
        else:
            label_clause = ""

        # Build WHERE clause based on match type
        if match_type == "exact":
            where_clause = f"n.{search_property} = $search_value"
        elif match_type == "starts_with":
            where_clause = (
                f"toLower(n.{search_property}) STARTS WITH toLower($search_value)"
            )
        elif match_type == "contains":
            where_clause = (
                f"toLower(n.{search_property}) CONTAINS toLower($search_value)"
            )
        else:
            raise QueryValidationError(
                f"Invalid match_type: {match_type}. "
                "Must be 'exact', 'starts_with', or 'contains'"
            )

        # Build query
        query = f"""
        MATCH (n{label_clause})
        WHERE {where_clause}
        RETURN n
        ORDER BY n.{search_property}
        LIMIT $limit
        """

        params = {"search_value": search_value, "limit": limit or self.max_results}

        self.validate_query_safety(query)
        return query, params

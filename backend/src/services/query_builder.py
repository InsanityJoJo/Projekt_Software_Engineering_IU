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


class AdminQueryBuilder(SafeQueryBuilder):
    """Builder for constructing safe administrative Cypher queries.

    This class extends SafeQueryBuilder to allow write operations while
    maintaining validation and parametrization. It is for administrative
    tasks like data import and should not be exposed to endusers.

    All operations use MERGE to check if nodes or raltionships exist.

    Inherits all validation methods from SafeQueryBuilder but alloes write keywords.
    All operations will still use parameterization to prevent cypher injection.
    """

    def __init__(self, max_results: int = 100):
        """Initialize the admin query builder.
        Args:
            max_results: Maximum number or results to return (safty limit).
        """
        super().__init__(max_results)

    def validate_query_safety(self, query: str) -> None:
        """Override parent method to allow write operations.

        Admin queries are allowed to contain CREATE, DELETE, SET, MERGE, etc.
        This method intentionally does nothing to allow these keywords.

        Args:
            query: The query string (not validated for write keywords).
        """
        pass

    def _validate_properties_dict(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Validate all properties in a dictionary.

        Args:
            properties: Dictionary of property names and values.

        Returns:
            Dict[str, Any]: The validated properties dictionary.

        Raises:
            QueryValidationError: If any property name is not allowed.
        """
        for prop_name in properties.keys():
            self.validate_property(prop_name)
        return properties

    def merge_node(
        self,
        label: str,
        match_properties: Dict[str, Any],
        set_properties: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """Build a query to merge a node

        Uses MERGE to find or create a node based on match_properties.
        Sets all properties from both match_properties and set_properties.

        Args:
            label : The node label.
            match_properties: Properties to match on
            set_properties: Optional additional properties to set.

        Returns:
            tuple: (query_string, parameters_dict)

        Raises:
            QueryValidationError: If label or properties are not allowed.

        Examples:
            >>> builder = AdminQueryBuilder()
            >>> query, params = builder.merge_node(
            ...     "ThreatActor",
            ...     {"name": "APT28"},
            ...     {"type": "Nation-State", "last_seen": "2024-01-01"}
            ... )
        """
        # validate inputs
        label = self.validate_label(label)
        match_properties = self._validate_properties_dict(match_properties)

        if not match_properties:
            raise QueryValidationError("match_properties cannot be empty for MERGE")

        # build match clause
        match_keys = ", ".join(
            [f"{key}: $match_{key}" for key in match_properties.keys()]
        )
        match_clause = f"{{{match_keys}}}"

        # Build SET clause for additional properties
        set_clause = ""
        if set_properties:
            set_properties = self._validate_properties_dict(set_properties)
            # Use += to merge properties (Neo4j map addition)
            set_clause = "SET n += $set_properties"

        # Build query
        query = f"""
        MERGE (n:{label} {match_clause})
        {set_clause}
        RETURN n
        """

        # Build parameters
        params = {f"match_{k}": v for k, v in match_properties.items()}
        if set_properties:
            params["set_properties"] = set_properties

        return query, params

    def merge_nodes_batch(
        self, nodes: List[Dict[str, Any]], match_property: str = "name"
    ) -> List[tuple[str, Dict[str, Any]]]:
        """Build separate queries to merge multiple nodes efficiently.

        This method groups nodes by their label and creates a separate query
        for each unique label type to avoid variable redeclaration issues in Cypher.
        Each query is executed separately.

        Args:
            nodes: List of node dictionaries, each containing:
                - label: str (node label)
                - properties: Dict (all node properties including match property)
            match_property: Property name to use for matching (default: "name").

        Returns:
            List of tuples: [(query_string, parameters_dict), ...]
            One tuple per unique label found in the nodes.

        Raises:
            QueryValidationError: If any label or property is not allowed.

        Examples:
            >>> builder = AdminQueryBuilder()
            >>> nodes = [
            ...     {"label": "ThreatActor", "properties": {"name": "APT28", "type": "Nation-State"}},
            ...     {"label": "Malware", "properties": {"name": "X-Agent", "family": "Sofacy"}}
            ... ]
            >>> queries = builder.merge_nodes_batch(nodes)
            >>> # Returns list with 2 queries, one for ThreatActor, one for Malware
        """
        # Validate match property
        match_property = self.validate_property(match_property)

        # Validate all nodes and group by label
        nodes_by_label = {}
        for node in nodes:
            if "label" not in node:
                raise QueryValidationError("Each node must have a 'label' field")
            if "properties" not in node:
                raise QueryValidationError("Each node must have a 'properties' field")

            label = self.validate_label(node["label"])
            properties = node["properties"]

            if match_property not in properties:
                raise QueryValidationError(
                    f"Each node must have '{match_property}' in properties"
                )

            self._validate_properties_dict(properties)

            # Group nodes by label
            if label not in nodes_by_label:
                nodes_by_label[label] = []
            nodes_by_label[label].append(properties)  # Store just properties

        # Build separate query for each label
        queries = []

        for label, properties_list in nodes_by_label.items():
            # Create unique parameter name for this label
            param_name = f"nodes_{label.replace(':', '_')}"
            params = {param_name: properties_list}

            # Build query for this label with count and label in return
            query = f"""
UNWIND ${param_name} AS props
MERGE (n:{label} {{{match_property}: props.{match_property}}})
SET n += props
RETURN count(n) AS count, '{label}' AS label"""

            queries.append((query, params))

        return queries

    def delete_node(
        self, label: str, property_name: str, property_value: Any
    ) -> tuple[str, Dict[str, Any]]:
        """Build a query to delete a node and its relationships.

        Uses DETACH DELETE to remove the node and all its relationships.

        Args:
            label: The node label.
            property_name: Property name to identify the node.
            property_value: Value to match the node.

        Returns:
            tuple: (query_string, parameters_dict)

        Raises:
            QueryValidationError: If label or property is not allowed.

        Examples:
            >>> builder = AdminQueryBuilder()
            >>> query, params = builder.delete_node(
            ...     "ThreatActor",
            ...     "name",
            ...     "APT28"
            ... )
        """
        # Validate inputs
        label = self.validate_label(label)
        property_name = self.validate_property(property_name)

        # Build query with DETACH DELETE to remove relationships too
        query = f"""
        MATCH (n:{label} {{{property_name}: $value}})
        DETACH DELETE n
        """

        params = {"value": property_value}

        return query, params

    def merge_relationship(
        self,
        from_label: str,
        from_value: Any,
        to_label: str,
        to_value: Any,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
        match_property: str = "name",
    ) -> tuple[str, Dict[str, Any]]:
        """Build a query to merge a relationship between two existing nodes.

        Both nodes must exist before creating the relationship. Uses MERGE to
        prevent duplicate relationships. Identifies nodes by a single property
        (default: 'name').

        Args:
            from_label: Label of the source node.
            from_value: Value to identify the source node.
            to_label: Label of the target node.
            to_value: Value to identify the target node.
            relationship_type: Type of the relationship.
            properties: Optional properties for the relationship.
            match_property: Property name to identify nodes (default: "name").

        Returns:
            tuple: (query_string, parameters_dict)

        Raises:
            QueryValidationError: If labels, properties, or relationship type not allowed.

        Examples:
            >>> builder = AdminQueryBuilder()
            >>> query, params = builder.merge_relationship(
            ...     "ThreatActor", "APT28",
            ...     "Malware", "X-Agent",
            ...     "USES",
            ...     {"source": "Report XYZ", "first_seen": "2015-06-01"}
            ... )
        """
        # Validate inputs
        from_label = self.validate_label(from_label)
        to_label = self.validate_label(to_label)
        relationship_type = self.validate_relationship(relationship_type)
        match_property = self.validate_property(match_property)

        # Validate relationship properties if provided
        if properties:
            properties = self._validate_properties_dict(properties)

        # Build query
        if properties:
            query = f"""
            MATCH (from:{from_label} {{{match_property}: $from_value}})
            MATCH (to:{to_label} {{{match_property}: $to_value}})
            MERGE (from)-[r:{relationship_type}]->(to)
            SET r += $properties
            RETURN from, r, to
            """
            params = {
                "from_value": from_value,
                "to_value": to_value,
                "properties": properties,
            }
        else:
            query = f"""
            MATCH (from:{from_label} {{{match_property}: $from_value}})
            MATCH (to:{to_label} {{{match_property}: $to_value}})
            MERGE (from)-[r:{relationship_type}]->(to)
            RETURN from, r, to
            """
            params = {"from_value": from_value, "to_value": to_value}

        return query, params

    def merge_relationships_batch(
        self,
        relationships: List[Dict[str, Any]],
        match_property: str = "name",
    ) -> List[tuple[str, Dict[str, Any]]]:
        """Build separate queries to merge multiple relationships efficiently.

        This method groups relationships by their pattern (from_label, to_label, type)
        and creates a separate query for each unique pattern to avoid variable
        redeclaration issues in Cypher.

        Args:
            relationships: List of relationship dictionaries, each containing:
                - from_label: str (source node label)
                - from_value: Any (source node identifier)
                - to_label: str (target node label)
                - to_value: Any (target node identifier)
                - type: str (relationship type)
                - properties: Optional[Dict] (relationship properties)
            match_property: Property name to identify nodes (default: "name").

        Returns:
            List of tuples: [(query_string, parameters_dict), ...]
            One tuple per unique relationship pattern.

        Raises:
            QueryValidationError: If any validation fails.

        Examples:
            >>> builder = AdminQueryBuilder()
            >>> relationships = [
            ...     {
            ...         "from_label": "ThreatActor",
            ...         "from_value": "APT28",
            ...         "to_label": "Malware",
            ...         "to_value": "X-Agent",
            ...         "type": "USES",
            ...         "properties": {"source": "Report 1"}
            ...     }
            ... ]
            >>> queries = builder.merge_relationships_batch(relationships)
            >>> # Returns list with queries, one per unique pattern
        """
        # Validate match property
        match_property = self.validate_property(match_property)

        # Validate all relationships and group by pattern
        rels_by_pattern = {}

        for rel in relationships:
            required_fields = [
                "from_label",
                "from_value",
                "to_label",
                "to_value",
                "type",
            ]
            if not all(k in rel for k in required_fields):
                raise QueryValidationError(
                    f"Each relationship must have: {', '.join(required_fields)}"
                )

            from_label = self.validate_label(rel["from_label"])
            to_label = self.validate_label(rel["to_label"])
            rel_type = self.validate_relationship(rel["type"])

            # Validate relationship properties if provided
            if "properties" in rel and rel["properties"]:
                self._validate_properties_dict(rel["properties"])

            # Create pattern key
            pattern = (from_label, to_label, rel_type)

            if pattern not in rels_by_pattern:
                rels_by_pattern[pattern] = []

            # Store simplified rel data
            rels_by_pattern[pattern].append(
                {
                    "from_value": rel["from_value"],
                    "to_value": rel["to_value"],
                    "properties": rel.get("properties", {}),
                }
            )

        # Build separate query for each pattern
        queries = []

        for (from_label, to_label, rel_type), rel_list in rels_by_pattern.items():
            # Create unique parameter name
            param_name = f"rels_{from_label}_{rel_type}_{to_label}".replace(":", "_")
            params = {param_name: rel_list}

            # Build query for this pattern with count and pattern info in return
            query = f"""
UNWIND ${param_name} AS relData
MATCH (from:{from_label} {{{match_property}: relData.from_value}})
MATCH (to:{to_label} {{{match_property}: relData.to_value}})
MERGE (from)-[r:{rel_type}]->(to)
SET r += relData.properties
RETURN count(r) AS count, '{from_label}' AS from_label, '{to_label}' AS to_label, '{rel_type}' AS type"""

            queries.append((query, params))

        return queries

    def delete_relationship(
        self,
        from_label: str,
        from_value: Any,
        to_label: str,
        to_value: Any,
        relationship_type: Optional[str] = None,
        match_property: str = "name",
    ) -> tuple[str, Dict[str, Any]]:
        """Build a query to delete a relationship between two nodes.

        Deletes the relationship but leaves both nodes intact. If relationship_type
        is not specified, deletes all relationships between the two nodes.

        Args:
            from_label: Label of the source node.
            from_value: Value to identify the source node.
            to_label: Label of the target node.
            to_value: Value to identify the target node.
            relationship_type: Optional specific relationship type to delete.
            match_property: Property name to identify nodes (default: "name").

        Returns:
            tuple: (query_string, parameters_dict)

        Raises:
            QueryValidationError: If labels, properties, or relationship type not allowed.

        Examples:
            >>> builder = AdminQueryBuilder()
            >>> # Delete specific relationship type
            >>> query, params = builder.delete_relationship(
            ...     "ThreatActor", "APT28",
            ...     "Malware", "X-Agent",
            ...     "USES"
            ... )
            >>> # Delete all relationships between nodes
            >>> query, params = builder.delete_relationship(
            ...     "ThreatActor", "APT28",
            ...     "Malware", "X-Agent"
            ... )
        """
        # Validate inputs
        from_label = self.validate_label(from_label)
        to_label = self.validate_label(to_label)
        match_property = self.validate_property(match_property)

        # Build relationship pattern
        if relationship_type:
            relationship_type = self.validate_relationship(relationship_type)
            rel_pattern = f"[r:{relationship_type}]"
        else:
            rel_pattern = "[r]"

        # Build query
        query = f"""
        MATCH (from:{from_label} {{{match_property}: $from_value}})
              -{rel_pattern}->
              (to:{to_label} {{{match_property}: $to_value}})
        DELETE r
        """

        params = {"from_value": from_value, "to_value": to_value}

        return query, params

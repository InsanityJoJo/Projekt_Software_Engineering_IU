"""Autocomplete service for node name suggestions.

This module provides efficient autocomplete functionality for searching
nodes in the Neo4j database. It uses case-insensitive prefix matching
and returns only the minimal data needed for suggestions.
"""

from typing import Optional
from src.driver import GraphDBDriver, ResultWrapper
from src.constants import ALLOWED_LABELS


class AutocompleteService:
    """Service for providing node name autocomplete suggestions."""

    def __init__(self, driver: GraphDBDriver):
        """Initialize the autocomplete service.

        Args:
            driver: The Neo4j database driver instance.
        """
        self.driver = driver

    def _validate_label(self, label: str) -> str:
        """Validate and sanitize label input.

        Args:
            label: Node label to validate

        Returns:
            Validated label string

        Raises:
            ValueError: If label is invalid
        """
        if label and label not in ALLOWED_LABELS:
            raise ValueError(f"Invalid label: {label}. Must be one of {ALLOWED_LABELS}")
        return label

    def suggest_node_names(
        self, prefix: str, label: Optional[str] = None, limit: int = 10
    ) -> ResultWrapper:
        """Get node name suggestions based on prefix.

        This method performs case-insensitive prefix matching on node names.
        It's optimized to return only names, not full node data.

        Args:
            prefix: The text prefix to match against node names.
            label: Optional node label to filter by (e.g., 'ThreatActor', 'Malware').
            limit: Maximum number of suggestions to return (default: 10).

        Returns:
            ResultWrapper: Contains list of matching names and metadata.
                Example data: [
                    {'name': 'ShadowGroup', 'label': 'ThreatActor', 'id': '4:abc123'},
                    {'name': 'Shadow Malware', 'label': 'Malware', 'id': '5:def456'}
                ]
        """
        # Sanitize input
        if not prefix or len(prefix.strip()) == 0:
            return ResultWrapper(success=True, data=[])

        prefix = prefix.strip()

        # Validate label if provided
        if label:
            try:
                label = self._validate_label(label)
            except ValueError as e:
                return ResultWrapper(success=False, error=str(e))

        # Build query based on whether label is specified
        if label:
            query = f"""
            MATCH (n:{label})
            WHERE toLower(n.name) STARTS WITH toLower($prefix)
            RETURN n.name AS name, labels(n)[0] AS label, elementId(n) AS id
            ORDER BY n.name
            LIMIT $limit
            """
        else:
            query = """
            MATCH (n)
            WHERE n.name IS NOT NULL 
              AND toLower(n.name) STARTS WITH toLower($prefix)
            RETURN n.name AS name, labels(n)[0] AS label, elementId(n) AS id
            ORDER BY n.name
            LIMIT $limit
            """

        params = {"prefix": prefix, "limit": limit}
        return self.driver.run_safe_query(query, params)

    def check_node_exists(
        self, name: str, label: Optional[str] = None
    ) -> ResultWrapper:
        """Check if a node with given name exists.

        This is a lightweight check that returns only boolean result,
        not the full node data.

        Args:
            name: The exact node name to check.
            label: Optional node label to filter by.

        Returns:
            ResultWrapper: Contains existence check result.
                Example data: [{'exists': True, 'count': 2}]
        """
        # Validate label if provided
        if label:
            try:
                label = self._validate_label(label)
            except ValueError as e:
                return ResultWrapper(success=False, error=str(e))

        if label:
            query = f"""
            MATCH (n:{label} {{name: $name}})
            RETURN count(n) AS count, count(n) > 0 AS exists
            """
        else:
            query = """
            MATCH (n {name: $name})
            RETURN count(n) AS count, count(n) > 0 AS exists
            """

        return self.driver.run_safe_query(query, {"name": name})

    def get_all_node_names(
        self, label: Optional[str] = None, max_nodes: int = 1000
    ) -> ResultWrapper:
        """Get all node names for frontend caching.

        WARNING: Use this carefully! For large databases, this can return
        a lot of data. Consider using pagination or limiting to specific labels.

        Args:
            label: Optional node label to filter by.
            max_nodes: Maximum number of names to return (safety limit).

        Returns:
            ResultWrapper: Contains all node names.
                Example data: [
                    {'name': 'ShadowGroup', 'label': 'ThreatActor'},
                    {'name': 'CryptoLocker-X', 'label': 'Malware'},
                    ...
                ]
        """
        # Validate label if provided
        if label:
            try:
                label = self._validate_label(label)
            except ValueError as e:
                return ResultWrapper(success=False, error=str(e))

        if label:
            query = f"""
            MATCH (n:{label})
            WHERE n.name IS NOT NULL
            RETURN DISTINCT n.name AS name, '{label}' AS label
            ORDER BY n.name
            LIMIT $max_nodes
            """
        else:
            query = """
            MATCH (n)
            WHERE n.name IS NOT NULL
            RETURN DISTINCT n.name AS name, labels(n)[0] AS label
            ORDER BY n.name
            LIMIT $max_nodes
            """

        return self.driver.run_safe_query(query, {"max_nodes": max_nodes})

    def fuzzy_search(
        self, search_term: str, label: Optional[str] = None, limit: int = 10
    ) -> ResultWrapper:
        """Perform fuzzy search on node names.

        This uses CONTAINS instead of STARTS WITH for more flexible matching.
        Results are ranked by relevance (prefix matches first, then substring matches).

        Args:
            search_term: The text to search for (can appear anywhere in name).
            label: Optional node label to filter by.
            limit: Maximum number of results to return.

        Returns:
            ResultWrapper: Contains matching nodes with relevance scoring.
                Example data: [
                    {'name': 'ShadowGroup', 'label': 'ThreatActor', 'id': '4:abc', 'relevance': 1},
                    {'name': 'AttackShadow', 'label': 'Campaign', 'id': '7:xyz', 'relevance': 2}
                ]
        """
        if not search_term or len(search_term.strip()) == 0:
            return ResultWrapper(success=True, data=[])

        search_term = search_term.strip()

        # Validate label if provided
        if label:
            try:
                label = self._validate_label(label)
            except ValueError as e:
                return ResultWrapper(success=False, error=str(e))

        if label:
            query = f"""
            MATCH (n:{label})
            WHERE toLower(n.name) CONTAINS toLower($search_term)
            RETURN n.name AS name, 
                   labels(n)[0] AS label, 
                   elementId(n) AS id,
                   CASE 
                     WHEN toLower(n.name) STARTS WITH toLower($search_term) THEN 1
                     ELSE 2
                   END AS relevance
            ORDER BY relevance, n.name
            LIMIT $limit
            """
        else:
            query = """
            MATCH (n)
            WHERE n.name IS NOT NULL 
              AND toLower(n.name) CONTAINS toLower($search_term)
            RETURN n.name AS name, 
                   labels(n)[0] AS label, 
                   elementId(n) AS id,
                   CASE 
                     WHEN toLower(n.name) STARTS WITH toLower($search_term) THEN 1
                     ELSE 2
                   END AS relevance
            ORDER BY relevance, n.name
            LIMIT $limit
            """

        return self.driver.run_safe_query(
            query, {"search_term": search_term, "limit": limit}
        )


# Example usage:
if __name__ == "__main__":
    # This is just for testing during development
    from driver import GraphDBDriver

    driver = GraphDBDriver(
        uri="bolt://localhost:7687", user="neo4j", password="password"
    )

    service = AutocompleteService(driver)

    # Test prefix search
    result = service.suggest_node_names("Sha", limit=5)
    if result.success:
        print("Prefix search results:")
        for item in result.data:
            print(f"  - {item['name']} ({item['label']})")

    # Test fuzzy search
    fuzzy_result = service.fuzzy_search("Shadow", limit=5)
    if fuzzy_result.success:
        print("\nFuzzy search results:")
        for item in fuzzy_result.data:
            print(
                f"  - {item['name']} ({item['label']}) - relevance: {item['relevance']}"
            )

    driver.close()

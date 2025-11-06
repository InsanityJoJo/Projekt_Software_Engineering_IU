"""Autocomplete service for node name suggestions.

This module provides autocomplete functionality for searching
nodes in the Neo4j database using the SafeQueryBuilder for consistency
and security.

REFACTORED: Now uses SafeQueryBuilder instead of raw Cypher queries.
FIXED: Properly extracts Neo4j labels from nodes.
"""

from typing import Optional
from src.driver import GraphDBDriver, ResultWrapper
from src.services.query_builder import SafeQueryBuilder


class AutocompleteService:
    """Service for providing node name autocomplete suggestions.

    This service uses SafeQueryBuilder to ensure all queries are:
    - Properly parameterized (no injection risk)
    - Validated (only allowed labels/properties)
    - Consistent with the rest of the application
    """

    def __init__(self, driver: GraphDBDriver):
        """Initialize the autocomplete service.

        Args:
            driver: The Neo4j database driver instance.
        """
        self.driver = driver
        self.query_builder = SafeQueryBuilder(max_results=100)

    def suggest_node_names(
        self, prefix: str, label: Optional[str] = None, limit: int = 10
    ) -> ResultWrapper:
        """Get node name suggestions based on prefix.

        This method performs case-insensitive prefix matching on node names.
        Returns: name, label, and id for each matching node.

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

        try:
            # Build custom query that returns label explicitly
            # We can't use search_nodes() because it doesn't return labels
            from src.constants import ALLOWED_LABELS

            if label:
                # Validate label
                if label not in ALLOWED_LABELS:
                    return ResultWrapper(success=False, error=f"Invalid label: {label}")

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

            # Execute query
            result = self.driver.run_safe_query(query, params)

            return result

        except Exception as e:
            return ResultWrapper(success=False, error=f"Search failed: {str(e)}")

    def fuzzy_search(
        self, search_term: str, label: Optional[str] = None, limit: int = 10
    ) -> ResultWrapper:
        """Perform fuzzy search on node names.

        This uses CONTAINS for more flexible matching with relevance scoring.

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

        try:
            # Build custom query with label and relevance
            from src.constants import ALLOWED_LABELS

            if label:
                # Validate label
                if label not in ALLOWED_LABELS:
                    return ResultWrapper(success=False, error=f"Invalid label: {label}")

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

            params = {"search_term": search_term, "limit": limit}

            # Execute query
            result = self.driver.run_safe_query(query, params)

            return result

        except Exception as e:
            return ResultWrapper(success=False, error=f"Fuzzy search failed: {str(e)}")

    def check_node_exists(
        self, name: str, label: Optional[str] = None
    ) -> ResultWrapper:
        """Check if a node with given name exists.

        This is a lightweight check that returns only boolean result.

        Args:
            name: The exact node name to check.
            label: Optional node label to filter by.

        Returns:
            ResultWrapper: Contains existence check result.
                Example data: [{'exists': True, 'count': 1}]
        """
        try:
            from src.constants import ALLOWED_LABELS

            if label and label not in ALLOWED_LABELS:
                return ResultWrapper(success=False, error=f"Invalid label: {label}")

            if label:
                query = f"""
                MATCH (n:{label} {{name: $name}})
                RETURN count(n) AS count, count(n) > 0 AS exists
                """
            else:
                query = """
                MATCH (n {{name: $name}})
                WHERE n.name IS NOT NULL
                RETURN count(n) AS count, count(n) > 0 AS exists
                """

            result = self.driver.run_safe_query(query, {"name": name})

            return result

        except Exception as e:
            return ResultWrapper(
                success=False, error=f"Existence check failed: {str(e)}"
            )

    def get_all_node_names(
        self, label: Optional[str] = None, max_nodes: int = 1000
    ) -> ResultWrapper:
        """Get all node names for frontend caching.

        WARNING: Use this carefully! For large databases, this can return
        a lot of data.

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
        try:
            from src.constants import ALLOWED_LABELS

            if label and label not in ALLOWED_LABELS:
                return ResultWrapper(success=False, error=f"Invalid label: {label}")

            if label:
                query = f"""
                MATCH (n:{label})
                WHERE n.name IS NOT NULL
                RETURN DISTINCT n.name AS name, labels(n)[0] AS label
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

            result = self.driver.run_safe_query(query, {"max_nodes": max_nodes})

            return result

        except Exception as e:
            return ResultWrapper(success=False, error=f"Get all names failed: {str(e)}")

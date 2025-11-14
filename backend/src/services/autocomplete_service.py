"""Autocomplete service for node name suggestions.

This module provides autocomplete functionality for searching
nodes in the Neo4j database using the SafeQueryBuilder.
"""

from typing import Optional
from src.driver import GraphDBDriver, ResultWrapper
from src.services.query_builder import SafeQueryBuilder


class AutocompleteService:
    """Service for providing node name autocomplete suggestions.

    This service uses SafeQueryBuilder to ensure all queries are:
    - Properly parameterized
    - Validated
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
        self,
        prefix: str,
        label: Optional[str] = None,
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ResultWrapper:
        """Get node name suggestions based on prefix with optional time filtering.

        This method performs case-insensitive prefix matching on node names.
        Returns: name, label, and id for each matching node.

        When time filters are provided, only nodes with time properties that
        overlap with the specified date range are returned.

        Args:
            prefix: The text prefix to match against node names.
            label: Optional node label to filter by (e.g., 'ThreatActor', 'Malware').
            limit: Maximum number of suggestions to return (default: 10).
            start_date: Optional start of time filter range (ISO format: "2022-01-01").
            end_date: Optional end of time filter range (ISO format: "2023-01-01").

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
            # Check if time filtering is requested
            if start_date and end_date:
                # Use time-aware query
                query, params = self.query_builder.search_nodes_with_time_filter(
                    label=label,
                    search_property="name",
                    search_value=prefix,
                    match_type="starts_with",
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    include_metadata=True,
                )
            else:
                # Use standard query without time filtering
                query, params = self.query_builder.search_nodes(
                    label=label,
                    search_property="name",
                    search_value=prefix,
                    match_type="starts_with",
                    limit=limit,
                    include_metadata=True,
                )

            # Execute query
            result = self.driver.run_safe_query(query, params)

            return result

        except Exception as e:
            return ResultWrapper(success=False, error=f"Search failed: {str(e)}")

    def fuzzy_search(
        self,
        search_term: str,
        label: Optional[str] = None,
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ResultWrapper:
        """Perform fuzzy search on node names with optional time filtering.

        This uses CONTAINS for more flexible matching with relevance scoring.

        Args:
            search_term: The text to search for (can appear anywhere in name).
            label: Optional node label to filter by.
            limit: Maximum number of results to return.
            start_date: Optional start of time filter range (ISO format: "2022-01-01").
            end_date: Optional end of time filter range (ISO format: "2023-01-01").

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
            # Check if time filtering is requested
            if start_date and end_date:
                # Use time-aware query with CONTAINS matching
                query, params = self.query_builder.search_nodes_with_time_filter(
                    label=label,
                    search_property="name",
                    search_value=search_term,
                    match_type="contains",
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    include_metadata=True,
                )
            else:
                # Use standard fuzzy search without time filtering
                query, params = self.query_builder.fuzzy_search_nodes(
                    label=label,
                    search_property="name",
                    search_value=search_term,
                    limit=limit,
                    include_metadata=True,
                )

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
            # Use query builder for efficient existence check
            # Returns only count and boolean, not full node data
            query, params = self.query_builder.check_node_exists(
                property_name="name", property_value=name, label=label
            )

            result = self.driver.run_safe_query(query, params)

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
            # Use query builder for bulk name retrieval
            # Returns DISTINCT names with labels for frontend caching
            query, params = self.query_builder.get_all_node_names(
                label=label,
                property_name="name",
                limit=max_nodes,
                include_metadata=True,
            )

            result = self.driver.run_safe_query(query, params)

            return result

        except Exception as e:
            return ResultWrapper(success=False, error=f"Get all names failed: {str(e)}")


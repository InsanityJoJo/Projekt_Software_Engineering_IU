"""Comprehensive tests for AutocompleteService.

This module tests the autocomplete service with various scenarios
to achieve high test coverage.
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.driver import ResultWrapper
from src.services.autocomplete_service import AutocompleteService
from src.constants import ALLOWED_LABELS


class TestAutocompleteServiceInit:
    """Test AutocompleteService initialization."""

    def test_init_with_driver(self):
        """Test service initialization with driver."""
        mock_driver = Mock()
        service = AutocompleteService(mock_driver)

        assert service.driver == mock_driver
        assert ALLOWED_LABELS is not None


class TestSuggestNodeNames:
    """Test suggest_node_names method."""

    def test_suggest_with_results(self):
        """Test suggestion returns results."""
        mock_driver = Mock()
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True,
            data=[
                {"name": "ShadowGroup", "label": "ThreatActor", "id": "1"},
                {"name": "ShadowMalware", "label": "Malware", "id": "2"},
            ],
        )
        service = AutocompleteService(mock_driver)

        result = service.suggest_node_names("Shad", limit=10)

        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0]["name"] == "ShadowGroup"

    def test_suggest_with_label_filter(self):
        """Test suggestion with label filter."""
        mock_driver = Mock()
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"name": "APT28", "label": "ThreatActor", "id": "1"}]
        )
        service = AutocompleteService(mock_driver)

        result = service.suggest_node_names("APT", label="ThreatActor", limit=10)

        assert result.success is True
        assert len(result.data) == 1

    def test_suggest_empty_prefix(self):
        """Test suggestion with empty prefix."""
        mock_driver = Mock()
        service = AutocompleteService(mock_driver)

        result = service.suggest_node_names("", limit=10)

        assert result.success is True
        assert len(result.data) == 0

    def test_suggest_whitespace_prefix(self):
        """Test suggestion with whitespace-only prefix."""
        mock_driver = Mock()
        service = AutocompleteService(mock_driver)

        result = service.suggest_node_names("   ", limit=10)

        assert result.success is True
        assert len(result.data) == 0

    def test_suggest_invalid_label(self):
        """Test suggestion with invalid label."""
        mock_driver = Mock()
        service = AutocompleteService(mock_driver)

        result = service.suggest_node_names("test", label="InvalidLabel", limit=10)

        assert result.success is False
        assert "not allowed" in result.error or "Invalid label" in result.error

    def test_suggest_no_label_filter(self):
        """Test suggestion without label filter."""
        mock_driver = Mock()
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True,
            data=[
                {"name": "Entity1", "label": "ThreatActor", "id": "1"},
                {"name": "Entity2", "label": "Malware", "id": "2"},
            ],
        )
        service = AutocompleteService(mock_driver)

        result = service.suggest_node_names("Ent", limit=10)

        assert result.success is True
        assert len(result.data) == 2

    def test_suggest_custom_limit(self):
        """Test suggestion with custom limit."""
        mock_driver = Mock()
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True,
            data=[
                {"name": f"Entity{i}", "label": "ThreatActor", "id": str(i)}
                for i in range(5)
            ],
        )
        service = AutocompleteService(mock_driver)

        result = service.suggest_node_names("Ent", limit=3)

        assert result.success is True
        # Driver is called with limit=3
        call_args = mock_driver.run_safe_query.call_args
        assert call_args[0][1]["limit"] == 3


class TestFuzzySearch:
    """Test fuzzy_search method."""

    def test_fuzzy_search_success(self):
        """Test successful fuzzy search."""
        mock_driver = Mock()
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True,
            data=[
                {"name": "DarkShadow", "label": "Campaign", "id": "1", "relevance": 2},
                {"name": "ShadowNet", "label": "Tool", "id": "2", "relevance": 1},
            ],
        )
        service = AutocompleteService(mock_driver)

        result = service.fuzzy_search("Shadow", limit=10)

        assert result.success is True
        assert len(result.data) == 2

    def test_fuzzy_search_with_label(self):
        """Test fuzzy search with label filter."""
        mock_driver = Mock()
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True,
            data=[
                {"name": "ShadowMalware", "label": "Malware", "id": "1", "relevance": 1}
            ],
        )
        service = AutocompleteService(mock_driver)

        result = service.fuzzy_search("Shadow", label="Malware", limit=10)

        assert result.success is True
        assert len(result.data) == 1

    def test_fuzzy_search_empty_term(self):
        """Test fuzzy search with empty search term."""
        mock_driver = Mock()
        service = AutocompleteService(mock_driver)

        result = service.fuzzy_search("", limit=10)

        assert result.success is True
        assert len(result.data) == 0

    def test_fuzzy_search_invalid_label(self):
        """Test fuzzy search with invalid label."""
        mock_driver = Mock()
        service = AutocompleteService(mock_driver)

        result = service.fuzzy_search("test", label="InvalidLabel", limit=10)

        assert result.success is False
        assert "not allowed" in result.error or "Invalid label" in result.error

    def test_fuzzy_search_relevance_ordering(self):
        """Test that fuzzy search orders by relevance."""
        mock_driver = Mock()
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True,
            data=[
                {
                    "name": "ShadowFirst",
                    "label": "ThreatActor",
                    "id": "1",
                    "relevance": 1,
                },
                {
                    "name": "AttackShadow",
                    "label": "Campaign",
                    "id": "2",
                    "relevance": 2,
                },
            ],
        )
        service = AutocompleteService(mock_driver)

        result = service.fuzzy_search("Shadow", limit=10)

        assert result.success is True
        # Lower relevance (1) should come first
        assert result.data[0]["relevance"] == 1


class TestCheckNodeExists:
    """Test check_node_exists method."""

    def test_check_exists_true(self):
        """Test checking for existing node."""
        mock_driver = Mock()
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"count": 1, "exists": True}]
        )
        service = AutocompleteService(mock_driver)

        result = service.check_node_exists("APT28")

        assert result.success is True
        assert result.data[0]["exists"] is True
        assert result.data[0]["count"] == 1

    def test_check_exists_false(self):
        """Test checking for non-existent node."""
        mock_driver = Mock()
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"count": 0, "exists": False}]
        )
        service = AutocompleteService(mock_driver)

        result = service.check_node_exists("NonExistent")

        assert result.success is True
        assert result.data[0]["exists"] is False

    def test_check_exists_with_label(self):
        """Test checking node existence with label filter."""
        mock_driver = Mock()
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"count": 1, "exists": True}]
        )
        service = AutocompleteService(mock_driver)

        result = service.check_node_exists("APT28", label="ThreatActor")

        assert result.success is True

    def test_check_exists_invalid_label(self):
        """Test checking existence with invalid label."""
        mock_driver = Mock()
        service = AutocompleteService(mock_driver)

        result = service.check_node_exists("test", label="InvalidLabel")

        assert result.success is False
        assert "not allowed" in result.error or "Invalid label" in result.error


class TestGetAllNodeNames:
    """Test get_all_node_names method."""

    def test_get_all_nodes_success(self):
        """Test getting all node names."""
        mock_driver = Mock()
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True,
            data=[
                {"name": "APT28", "label": "ThreatActor"},
                {"name": "X-Agent", "label": "Malware"},
                {"name": "Campaign1", "label": "Campaign"},
            ],
        )
        service = AutocompleteService(mock_driver)

        result = service.get_all_node_names(max_nodes=1000)

        assert result.success is True
        assert len(result.data) == 3

    def test_get_all_nodes_with_label_filter(self):
        """Test getting all nodes filtered by label."""
        mock_driver = Mock()
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True,
            data=[
                {"name": "APT28", "label": "ThreatActor"},
                {"name": "APT29", "label": "ThreatActor"},
            ],
        )
        service = AutocompleteService(mock_driver)

        result = service.get_all_node_names(label="ThreatActor", max_nodes=1000)

        assert result.success is True
        assert len(result.data) == 2
        assert all(item["label"] == "ThreatActor" for item in result.data)

    def test_get_all_nodes_custom_limit(self):
        """Test getting all nodes with custom limit."""
        mock_driver = Mock()
        mock_driver.run_safe_query.return_value = ResultWrapper(success=True, data=[])
        service = AutocompleteService(mock_driver)

        result = service.get_all_node_names(max_nodes=500)

        # Check that limit was passed to driver
        call_args = mock_driver.run_safe_query.call_args
        assert call_args[0][1]["limit"] == 500

    def test_get_all_nodes_invalid_label(self):
        """Test getting all nodes with invalid label."""
        mock_driver = Mock()
        service = AutocompleteService(mock_driver)

        result = service.get_all_node_names(label="InvalidLabel")

        assert result.success is False
        assert "not allowed" in result.error or "Invalid label" in result.error


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""

    def test_autocomplete_workflow(self):
        """Test complete autocomplete workflow."""
        mock_driver = Mock()
        service = AutocompleteService(mock_driver)

        # User types "Sha"
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True,
            data=[
                {"name": "ShadowGroup", "label": "ThreatActor", "id": "1"},
                {"name": "ShadowCampaign", "label": "Campaign", "id": "2"},
            ],
        )

        result = service.suggest_node_names("Sha", limit=10)

        assert result.success is True
        assert len(result.data) == 2

    def test_fallback_to_fuzzy_search(self):
        """Test fallback from prefix to fuzzy search."""
        mock_driver = Mock()
        service = AutocompleteService(mock_driver)

        # First: prefix search returns few results
        prefix_result = ResultWrapper(
            success=True, data=[{"name": "Shadow", "label": "ThreatActor", "id": "1"}]
        )

        # Then: fuzzy search returns more
        fuzzy_result = ResultWrapper(
            success=True,
            data=[
                {"name": "DarkShadow", "label": "Campaign", "id": "2", "relevance": 2},
                {"name": "ShadowNet", "label": "Tool", "id": "3", "relevance": 2},
            ],
        )

        # This would be handled by the handler, but we can test both methods work
        prefix = service.suggest_node_names("Shad", limit=10)
        mock_driver.run_safe_query.return_value = prefix_result
        prefix = service.suggest_node_names("Shad", limit=10)

        mock_driver.run_safe_query.return_value = fuzzy_result
        fuzzy = service.fuzzy_search("Shad", limit=10)

        assert prefix.success is True
        assert fuzzy.success is True

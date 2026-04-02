"""Additional tests for AutocompleteService exception handling paths.

These tests target the previously untested exception handler branches
in autocomplete_service.py, specifically:
- ServiceUnavailable / SessionExpired (database connection errors)
- Neo4jError (general database errors)
- Unexpected Exception fallback

These paths cannot be triggered by a mock that simply returns ResultWrapper,
because the exceptions are raised BEFORE run_safe_query is called -- they
come from the query_builder or the driver itself. We simulate them by
patching the driver's run_safe_query to raise the exception directly,
or by patching the query_builder methods on the service instance.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from neo4j.exceptions import Neo4jError, ServiceUnavailable, SessionExpired

from src.driver import ResultWrapper
from src.services.autocomplete_service import AutocompleteService
from src.services.query_builder import QueryValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_service_with_raising_driver(exception: Exception) -> AutocompleteService:
    """Create an AutocompleteService whose driver raises the given exception.

    The query builder will succeed (build a valid query), but the driver's
    run_safe_query will raise the supplied exception. This simulates a live
    database that becomes unavailable mid-operation.

    Args:
        exception: The exception instance the driver should raise.

    Returns:
        AutocompleteService with the configured mock driver.
    """
    mock_driver = Mock()
    mock_driver.run_safe_query.side_effect = exception
    return AutocompleteService(mock_driver)


# ---------------------------------------------------------------------------
# suggest_node_names – exception paths
# ---------------------------------------------------------------------------


class TestSuggestNodeNamesExceptions:
    """Test exception handling in suggest_node_names."""

    def test_service_unavailable_returns_error_result(self):
        """ServiceUnavailable from driver is caught and wrapped.

        Simulates the database going offline after a valid query is built.
        Erwartet: success=False, error message mentions unavailability.
        """
        service = make_service_with_raising_driver(
            ServiceUnavailable("Connection refused")
        )

        result = service.suggest_node_names("APT", limit=10)

        assert result.success is False
        assert "unavailable" in result.error.lower()

    def test_session_expired_returns_error_result(self):
        """SessionExpired from driver is caught and wrapped.

        Simulates an expired database session during prefix search.
        Erwartet: success=False, error message mentions unavailability.
        """
        service = make_service_with_raising_driver(
            SessionExpired("Session has expired")
        )

        result = service.suggest_node_names("APT", limit=10)

        assert result.success is False
        assert "unavailable" in result.error.lower()

    def test_neo4j_error_returns_error_result(self):
        """Generic Neo4jError from driver is caught and wrapped.

        Simulates a database error such as a constraint violation
        or internal Neo4j failure.
        Erwartet: success=False, error message contains database error info.
        """
        service = make_service_with_raising_driver(
            Neo4jError("Internal Neo4j error")
        )

        result = service.suggest_node_names("APT", limit=10)

        assert result.success is False
        assert result.error is not None

    def test_unexpected_exception_returns_error_result(self):
        """Unexpected exception from driver is caught by the fallback handler.

        Simulates an unforeseen error (e.g., memory error, network issue)
        that is not a known Neo4j exception type.
        Erwartet: success=False, generic error message returned.
        """
        service = make_service_with_raising_driver(
            RuntimeError("Completely unexpected")
        )

        result = service.suggest_node_names("APT", limit=10)

        assert result.success is False
        assert result.error is not None

    def test_service_unavailable_with_time_filter(self):
        """ServiceUnavailable is handled correctly when time filters are active.

        The time-filter code path goes through a different query builder method
        (search_nodes_with_time_filter), but the exception handling is the same.
        Erwartet: success=False, error message mentions unavailability.
        """
        service = make_service_with_raising_driver(
            ServiceUnavailable("No route to host")
        )

        result = service.suggest_node_names(
            "APT",
            limit=10,
            start_date="2020-01-01",
            end_date="2024-01-01",
        )

        assert result.success is False
        assert "unavailable" in result.error.lower()


# ---------------------------------------------------------------------------
# fuzzy_search – exception paths
# ---------------------------------------------------------------------------


class TestFuzzySearchExceptions:
    """Test exception handling in fuzzy_search."""

    def test_service_unavailable_returns_error_result(self):
        """ServiceUnavailable from driver is caught in fuzzy_search.

        Erwartet: success=False, error message mentions unavailability.
        """
        service = make_service_with_raising_driver(
            ServiceUnavailable("Connection refused")
        )

        result = service.fuzzy_search("shadow", limit=10)

        assert result.success is False
        assert "unavailable" in result.error.lower()

    def test_session_expired_returns_error_result(self):
        """SessionExpired from driver is caught in fuzzy_search.

        Erwartet: success=False, error message mentions unavailability.
        """
        service = make_service_with_raising_driver(
            SessionExpired("Session has expired")
        )

        result = service.fuzzy_search("shadow", limit=10)

        assert result.success is False
        assert "unavailable" in result.error.lower()

    def test_neo4j_error_returns_error_result(self):
        """Generic Neo4jError from driver is caught in fuzzy_search.

        Erwartet: success=False, error contains database error info.
        """
        service = make_service_with_raising_driver(
            Neo4jError("Query execution failed")
        )

        result = service.fuzzy_search("shadow", limit=10)

        assert result.success is False
        assert result.error is not None

    def test_unexpected_exception_returns_error_result(self):
        """Unexpected exception is caught by the fallback handler in fuzzy_search.

        Erwartet: success=False, generic error message.
        """
        service = make_service_with_raising_driver(
            ValueError("Unexpected value error")
        )

        result = service.fuzzy_search("shadow", limit=10)

        assert result.success is False
        assert result.error is not None

    def test_service_unavailable_with_time_filter(self):
        """ServiceUnavailable is handled when time filters are active in fuzzy_search.

        Erwartet: success=False, error message mentions unavailability.
        """
        service = make_service_with_raising_driver(
            ServiceUnavailable("Timeout")
        )

        result = service.fuzzy_search(
            "shadow",
            limit=10,
            start_date="2020-01-01",
            end_date="2024-01-01",
        )

        assert result.success is False
        assert "unavailable" in result.error.lower()


# ---------------------------------------------------------------------------
# check_node_exists – exception paths
# ---------------------------------------------------------------------------


class TestCheckNodeExistsExceptions:
    """Test exception handling in check_node_exists."""

    def test_service_unavailable_returns_error_result(self):
        """ServiceUnavailable from driver is caught in check_node_exists.

        Erwartet: success=False, error message mentions unavailability.
        """
        service = make_service_with_raising_driver(
            ServiceUnavailable("DB offline")
        )

        result = service.check_node_exists("APT28")

        assert result.success is False
        assert "unavailable" in result.error.lower()

    def test_session_expired_returns_error_result(self):
        """SessionExpired from driver is caught in check_node_exists.

        Erwartet: success=False, error message mentions unavailability.
        """
        service = make_service_with_raising_driver(
            SessionExpired("Session gone")
        )

        result = service.check_node_exists("APT28")

        assert result.success is False
        assert "unavailable" in result.error.lower()

    def test_neo4j_error_returns_error_result(self):
        """Generic Neo4jError is caught in check_node_exists.

        Erwartet: success=False, error contains database error info.
        """
        service = make_service_with_raising_driver(
            Neo4jError("Constraint error")
        )

        result = service.check_node_exists("APT28")

        assert result.success is False
        assert result.error is not None

    def test_unexpected_exception_returns_error_result(self):
        """Unexpected exception is caught by fallback in check_node_exists.

        Erwartet: success=False, generic error message.
        """
        service = make_service_with_raising_driver(
            RuntimeError("Something exploded")
        )

        result = service.check_node_exists("APT28")

        assert result.success is False
        assert result.error is not None


# ---------------------------------------------------------------------------
# get_all_node_names – exception paths
# ---------------------------------------------------------------------------


class TestGetAllNodeNamesExceptions:
    """Test exception handling in get_all_node_names."""

    def test_service_unavailable_returns_error_result(self):
        """ServiceUnavailable from driver is caught in get_all_node_names.

        Erwartet: success=False, error message mentions unavailability.
        """
        service = make_service_with_raising_driver(
            ServiceUnavailable("DB unreachable")
        )

        result = service.get_all_node_names()

        assert result.success is False
        assert "unavailable" in result.error.lower()

    def test_session_expired_returns_error_result(self):
        """SessionExpired from driver is caught in get_all_node_names.

        Erwartet: success=False, error message mentions unavailability.
        """
        service = make_service_with_raising_driver(
            SessionExpired("Session expired")
        )

        result = service.get_all_node_names()

        assert result.success is False
        assert "unavailable" in result.error.lower()

    def test_neo4j_error_returns_error_result(self):
        """Generic Neo4jError is caught in get_all_node_names.

        Erwartet: success=False, error contains database error info.
        """
        service = make_service_with_raising_driver(
            Neo4jError("Index not found")
        )

        result = service.get_all_node_names()

        assert result.success is False
        assert result.error is not None

    def test_unexpected_exception_returns_error_result(self):
        """Unexpected exception is caught by fallback in get_all_node_names.

        Erwartet: success=False, generic error message.
        """
        service = make_service_with_raising_driver(
            MemoryError("Out of memory")
        )

        result = service.get_all_node_names()

        assert result.success is False
        assert result.error is not None

    def test_with_label_filter_and_service_unavailable(self):
        """ServiceUnavailable is handled when label filter is active.

        Erwartet: success=False, error message mentions unavailability.
        """
        service = make_service_with_raising_driver(
            ServiceUnavailable("Timeout during bulk retrieval")
        )

        result = service.get_all_node_names(label="ThreatActor")

        assert result.success is False
        assert "unavailable" in result.error.lower()

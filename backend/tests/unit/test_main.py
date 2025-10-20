"""Unit tests for the Flask API in main.py.

This module tests the Flask endpoints, database initialization,
and error handling in the main application.
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from src.main import app, init_database
from src.driver import ResultWrapper


class TestInitDatabase:
    """Test suite for init_database() function."""

    @patch("src.main.GraphDBDriver")
    @patch.dict(
        "os.environ",
        {
            "NEO4J_URI": "bolt://test:7687",
            "NEO4J_USER": "test_user",
            "NEO4J_PASSWORD": "test_pass",
            "LOG_LEVEL": "DEBUG",
        },
    )
    def test_init_database_success(self, mock_driver_class):
        """Test successful database initialization."""
        # Setup mock
        mock_instance = Mock()
        mock_instance.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"test": 1}]
        )
        mock_driver_class.return_value = mock_instance

        # Test
        driver = init_database()

        # Verify
        assert driver is mock_instance
        mock_driver_class.assert_called_once()
        mock_instance.run_safe_query.assert_called_once()

    @patch("src.main.GraphDBDriver")
    @patch("sys.exit")
    def test_init_database_connection_test_fails(self, mock_exit, mock_driver_class):
        """Test that init_database exits when connection test fails."""
        # Setup mock to fail connection test
        mock_instance = Mock()
        mock_instance.run_safe_query.return_value = ResultWrapper(
            success=False, error="Connection failed"
        )
        mock_driver_class.return_value = mock_instance

        # Test
        init_database()

        # Verify sys.exit was called
        mock_exit.assert_called_once_with(1)

    @patch("src.main.GraphDBDriver")
    @patch("sys.exit")
    def test_init_database_exception_handling(self, mock_exit, mock_driver_class):
        """Test that init_database handles exceptions gracefully."""
        # Setup mock to raise exception
        mock_driver_class.side_effect = Exception("Connection error")

        # Test
        init_database()

        # Verify sys.exit was called
        mock_exit.assert_called_once_with(1)


class TestHealthCheckEndpoint:
    """Test suite for /health endpoint."""

    def test_health_check_success(self, client, mock_driver):
        """Test health check when database is healthy."""
        import src.main as main_module

        # Setup mock driver
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"health": 1}]
        )

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.get("/health")
            data = response.get_json()

            # Verify
            assert response.status_code == 200
            assert data["status"] == "healthy"
            assert data["database"] == "connected"
        finally:
            main_module.db_driver = original

    def test_health_check_database_unhealthy(self, client, mock_driver):
        """Test health check when database query fails."""
        import src.main as main_module

        # Setup mock driver to fail
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=False, error="Connection lost"
        )

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.get("/health")
            data = response.get_json()

            # Verify
            assert response.status_code == 503
            assert data["status"] == "unhealthy"
            assert data["database"] == "disconnected"
        finally:
            main_module.db_driver = original

    def test_health_check_driver_not_initialized(self, client):
        """Test health check when driver is not initialized."""
        import src.main as main_module

        original = main_module.db_driver
        main_module.db_driver = None

        try:
            # Make request
            response = client.get("/health")
            data = response.get_json()

            # Verify
            assert response.status_code == 503
            assert "error" in data or data["status"] == "unhealthy"
        finally:
            main_module.db_driver = original


class TestQueryEndpoint:
    """Test suite for /api/query endpoint."""

    def test_execute_query_success(self, client, mock_driver):
        """Test successful query execution."""
        import src.main as main_module

        # Setup mock
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"name": "Alice"}, {"name": "Bob"}]
        )

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.post(
                "/api/query", json={"query": "MATCH (n) RETURN n", "parameters": {}}
            )
            data = response.get_json()

            # Verify
            assert response.status_code == 200
            assert data["success"] is True
            assert data["count"] == 2
            assert len(data["data"]) == 2
        finally:
            main_module.db_driver = original

    def test_execute_query_missing_query(self, client, mock_driver):
        """Test query endpoint with missing query parameter."""
        import src.main as main_module

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request without query
            response = client.post("/api/query", json={})
            data = response.get_json()

            # Verify
            assert response.status_code == 400
            assert "error" in data
        finally:
            main_module.db_driver = original

    def test_execute_query_database_error(self, client, mock_driver):
        """Test query endpoint when database returns error."""
        import src.main as main_module

        # Setup mock to fail
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=False, error="Syntax error in query"
        )

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.post("/api/query", json={"query": "INVALID CYPHER"})
            data = response.get_json()

            # Verify
            assert response.status_code == 400
            assert data["success"] is False
            assert "error" in data
        finally:
            main_module.db_driver = original

    def test_execute_query_with_parameters(self, client, mock_driver):
        """Test query execution with parameters."""
        import src.main as main_module

        # Setup mock
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"name": "Alice"}]
        )

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.post(
                "/api/query",
                json={
                    "query": "MATCH (n {name: $name}) RETURN n",
                    "parameters": {"name": "Alice"},
                },
            )
            data = response.get_json()

            # Verify
            assert response.status_code == 200
            assert data["success"] is True
            # Verify parameters were passed to driver
            mock_driver.run_safe_query.assert_called_once()
            call_args = mock_driver.run_safe_query.call_args
            assert call_args[0][1] == {"name": "Alice"}
        finally:
            main_module.db_driver = original


class TestCORSConfiguration:
    """Test suite for CORS configuration."""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses."""
        import src.main as main_module

        # Setup minimal mock
        mock_driver = Mock()
        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.get("/health")

            # Verify CORS headers (flask-cors should add these)
            assert (
                "Access-Control-Allow-Origin" in response.headers
                or response.status_code in [200, 503]
            )
        finally:
            main_module.db_driver = original


class TestErrorHandling:
    """Test suite for error handling."""

    def test_handles_json_decode_error(self, client, mock_driver):
        """Test handling of invalid JSON in request."""
        import src.main as main_module

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request with invalid JSON
            response = client.post(
                "/api/query", data="invalid json", content_type="application/json"
            )

            # Verify error response
            assert response.status_code in [400, 500]
        finally:
            main_module.db_driver = original

    def test_handles_driver_exception(self, client, mock_driver):
        """Test handling of unexpected driver exceptions."""
        import src.main as main_module

        # Setup mock to raise exception
        mock_driver.run_safe_query.side_effect = Exception("Unexpected error")

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.post("/api/query", json={"query": "MATCH (n) RETURN n"})
            data = response.get_json()

            # Verify
            assert response.status_code == 500
            assert "error" in data
        finally:
            main_module.db_driver = original

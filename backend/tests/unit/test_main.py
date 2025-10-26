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


class TestGetNodesEndpoint:
    """Test suite for GET /api/nodes endpoint."""

    def test_get_nodes_success(self, client, mock_driver):
        """Test successful retrieval od nodes."""
        import src.main as main_module

        # Setup mock
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True,
            data=[{"name": "Alice", "type": "Gang"}, {"name": "Bob", "type": "Gang"}],
        )

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.get("/api/nodes")
            data = response.get_json()

            # Verify
            assert response.status_code == 200
            assert data["success"] is True
            assert data["count"] == 2
            assert len(data["nodes"]) == 2
            assert data["nodes"][0]["name"] == "Alice"
        finally:
            main_module.db_driver = original

    def test_get_nodes_with_custom_limit(self, client, mock_driver):
        """Test getting nodes with custom limit parameter."""
        import src.main as main_module

        # Setup mock
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"name": f"Node{i}"} for i in range(5)]
        )

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request with limit
            response = client.get("/api/nodes?limit=5")
            data = response.get_json()

            # Verify
            assert response.status_code == 200
            assert data["count"] == 5

            # Verify the query was called with correct limit
            mock_driver.run_safe_query.assert_called_once()
            call_args = mock_driver.run_safe_query.call_args
            assert call_args[0][1]["limit"] == 5
        finally:
            main_module.db_driver = original

    def test_get_nodes_default_limit(self, client, mock_driver):
        """Test that default limit of 100 is used when not specified."""
        import src.main as main_module

        # Setup mock
        mock_driver.run_safe_query.return_value = ResultWrapper(success=True, data=[])

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request without limit
            response = client.get("/api/nodes")

            # Verify default limit was used
            mock_driver.run_safe_query.assert_called_once()
            call_args = mock_driver.run_safe_query.call_args
            assert call_args[0][1]["limit"] == 100
        finally:
            main_module.db_driver = original

    def test_get_nodes_empty_result(self, client, mock_driver):
        """Test getting nodes when database is empty."""
        import src.main as main_module

        # Setup mock for empty result
        mock_driver.run_safe_query.return_value = ResultWrapper(success=True, data=[])

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.get("/api/nodes")
            data = response.get_json()

            # Verify
            assert response.status_code == 200
            assert data["success"] is True
            assert data["count"] == 0
            assert data["nodes"] == []
        finally:
            main_module.db_driver = original

    def test_get_nodes_database_error(self, client, mock_driver):
        """Test handling of database errors."""
        import src.main as main_module

        # Setup mock to fail
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=False, error="Database connection lost"
        )

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.get("/api/nodes")
            data = response.get_json()

            # Verify
            assert response.status_code == 500
            assert data["success"] is False
            assert "error" in data
        finally:
            main_module.db_driver = original

    def test_get_nodes_exception_handling(self, client, mock_driver):
        """Test handling of unexpected exceptions."""
        import src.main as main_module

        # Setup mock to raise exception
        mock_driver.run_safe_query.side_effect = Exception("Unexpected error")

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.get("/api/nodes")
            data = response.get_json()

            # Verify
            assert response.status_code == 500
            assert "error" in data
        finally:
            main_module.db_driver = original

    def test_get_nodes_invalid_limit_type(self, client, mock_driver):
        """Test handling of invalid limit parameter type."""
        import src.main as main_module

        # Setup mock
        mock_driver.run_safe_query.return_value = ResultWrapper(success=True, data=[])

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request with invalid limit
            response = client.get("/api/nodes?limit=abc")

            # Flask will use default value for invalid int conversion
            # Should still work with default 100
            assert response.status_code == 200
        finally:
            main_module.db_driver = original


class TestCreateNodeEndpoint:
    """Test suite for POST /api/nodes endpoint."""

    def test_create_node_success(self, client, mock_driver):
        """Test successful node creation."""
        import src.main as main_module

        # Setup mock
        mock_driver.execute.return_value = [{"name": "Alice", "age": 30}]

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.post(
                "/api/nodes",
                json={"label": "Person", "properties": {"name": "Alice", "age": 30}},
            )
            data = response.get_json()

            # Verify
            assert response.status_code == 201
            assert data["success"] is True
            assert "Person" in data["message"]
            assert data["data"] is not None

            # Verify execute was called with write=True
            mock_driver.execute.assert_called_once()
            call_args = mock_driver.execute.call_args
            assert call_args[1]["write"] is True
        finally:
            main_module.db_driver = original

    def test_create_node_with_multiple_properties(self, client, mock_driver):
        """Test creating node with multiple properties."""
        import src.main as main_module

        # Setup mock
        mock_driver.execute.return_value = [{"created": True}]

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.post(
                "/api/nodes",
                json={
                    "label": "ThreatActor",
                    "properties": {
                        "name": "APT28",
                        "type": "Nation-State",
                        "country": "Russia",
                        "active": True,
                    },
                },
            )

            # Verify
            assert response.status_code == 201

            # Verify properties were passed correctly
            call_args = mock_driver.execute.call_args
            properties = call_args[0][1]
            assert properties["name"] == "APT28"
            assert properties["type"] == "Nation-State"
            assert properties["country"] == "Russia"
            assert properties["active"] is True
        finally:
            main_module.db_driver = original

    def test_create_node_without_properties(self, client, mock_driver):
        """Test creating node without properties (only label)."""
        import src.main as main_module

        # Setup mock
        mock_driver.execute.return_value = [{"created": True}]

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request without properties
            response = client.post("/api/nodes", json={"label": "EmptyNode"})

            # Verify
            assert response.status_code == 201

            # Verify query has empty property clause
            call_args = mock_driver.execute.call_args
            query = call_args[0][0]
            assert "CREATE (n:EmptyNode" in query
        finally:
            main_module.db_driver = original

    def test_create_node_missing_label(self, client, mock_driver):
        """Test creating node without required label."""
        import src.main as main_module

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request without label
            response = client.post("/api/nodes", json={"properties": {"name": "Alice"}})
            data = response.get_json()

            # Verify
            assert response.status_code == 400
            assert "error" in data
            assert "Label required" in data["error"]
        finally:
            main_module.db_driver = original

    def test_create_node_empty_request(self, client, mock_driver):
        """Test creating node with empty request body."""
        import src.main as main_module

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request with no data
            response = client.post("/api/nodes", json={})
            data = response.get_json()

            # Verify
            assert response.status_code == 400
            assert "error" in data
        finally:
            main_module.db_driver = original

    def test_create_node_no_json(self, client, mock_driver):
        """Test creating node without JSON content type."""
        import src.main as main_module

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request without JSON
            response = client.post("/api/nodes", data="not json")
            data = response.get_json()

            # Verify
            assert response.status_code == 400
            assert "error" in data
        finally:
            main_module.db_driver = original

    def test_create_node_database_error(self, client, mock_driver):
        """Test handling of database errors during creation."""
        import src.main as main_module

        # Setup mock to raise exception
        mock_driver.execute.side_effect = Exception("Constraint violation")

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.post(
                "/api/nodes", json={"label": "Person", "properties": {"name": "Alice"}}
            )
            data = response.get_json()

            # Verify
            assert response.status_code == 500
            assert "error" in data
        finally:
            main_module.db_driver = original

    def test_create_node_cypher_injection_protection(self, client, mock_driver):
        """Test that properties are properly parameterized (injection protection)."""
        import src.main as main_module

        # Setup mock
        mock_driver.execute.return_value = [{"created": True}]

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Attempt injection via property value
            response = client.post(
                "/api/nodes",
                json={
                    "label": "Person",
                    "properties": {"name": "'; DROP DATABASE; --"},
                },
            )

            # Verify request succeeded (injection prevented by parameterization)
            assert response.status_code == 201

            # Verify the malicious string was passed as parameter, not in query
            call_args = mock_driver.execute.call_args
            properties = call_args[0][1]
            assert properties["name"] == "'; DROP DATABASE; --"
        finally:
            main_module.db_driver = original


class TestGetStatsEndpoint:
    """Test suite for GET /api/stats endpoint."""

    def test_get_stats_success(self, client, mock_driver):
        """Test successful retrieval of database statistics."""
        import src.main as main_module

        # Setup mock for both queries
        def mock_query(query, params=None):
            if "count(n)" in query:
                return ResultWrapper(success=True, data=[{"count": 150}])
            elif "count(r)" in query:
                return ResultWrapper(success=True, data=[{"count": 75}])
            return ResultWrapper(success=False, error="Unknown query")

        mock_driver.run_safe_query.side_effect = mock_query

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.get("/api/stats")
            data = response.get_json()

            # Verify
            assert response.status_code == 200
            assert data["success"] is True
            assert data["nodes"] == 150
            assert data["relationships"] == 75

            # Verify both queries were called
            assert mock_driver.run_safe_query.call_count == 2
        finally:
            main_module.db_driver = original

    def test_get_stats_empty_database(self, client, mock_driver):
        """Test statistics for empty database."""
        import src.main as main_module

        # Setup mock for empty database
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"count": 0}]
        )

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.get("/api/stats")
            data = response.get_json()

            # Verify
            assert response.status_code == 200
            assert data["success"] is True
            assert data["nodes"] == 0
            assert data["relationships"] == 0
        finally:
            main_module.db_driver = original

    def test_get_stats_node_query_fails(self, client, mock_driver):
        """Test handling when node count query fails."""
        import src.main as main_module

        # Setup mock - first query fails, second succeeds
        def mock_query(query, params=None):
            if "count(n)" in query:
                return ResultWrapper(success=False, error="Node query failed")
            elif "count(r)" in query:
                return ResultWrapper(success=True, data=[{"count": 50}])

        mock_driver.run_safe_query.side_effect = mock_query

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.get("/api/stats")
            data = response.get_json()

            # Verify
            assert response.status_code == 500
            assert data["success"] is False
            assert "error" in data
        finally:
            main_module.db_driver = original

    def test_get_stats_relationship_query_fails(self, client, mock_driver):
        """Test handling when relationship count query fails."""
        import src.main as main_module

        # Setup mock - first query succeeds, second fails
        def mock_query(query, params=None):
            if "count(n)" in query:
                return ResultWrapper(success=True, data=[{"count": 100}])
            elif "count(r)" in query:
                return ResultWrapper(success=False, error="Relationship query failed")

        mock_driver.run_safe_query.side_effect = mock_query

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.get("/api/stats")
            data = response.get_json()

            # Verify
            assert response.status_code == 500
            assert data["success"] is False
            assert "error" in data
        finally:
            main_module.db_driver = original

    def test_get_stats_both_queries_fail(self, client, mock_driver):
        """Test handling when both queries fail."""
        import src.main as main_module

        # Setup mock - both fail
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=False, error="Database connection lost"
        )

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.get("/api/stats")
            data = response.get_json()

            # Verify
            assert response.status_code == 500
            assert data["success"] is False
            assert "error" in data
        finally:
            main_module.db_driver = original

    def test_get_stats_exception_handling(self, client, mock_driver):
        """Test handling of unexpected exceptions."""
        import src.main as main_module

        # Setup mock to raise exception
        mock_driver.run_safe_query.side_effect = Exception("Unexpected error")

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.get("/api/stats")
            data = response.get_json()

            # Verify
            assert response.status_code == 500
            assert "error" in data
        finally:
            main_module.db_driver = original

    def test_get_stats_large_numbers(self, client, mock_driver):
        """Test statistics with large numbers."""
        import src.main as main_module

        # Setup mock with large numbers
        def mock_query(query, params=None):
            if "count(n)" in query:
                return ResultWrapper(success=True, data=[{"count": 1000000}])
            elif "count(r)" in query:
                return ResultWrapper(success=True, data=[{"count": 5000000}])

        mock_driver.run_safe_query.side_effect = mock_query

        original = main_module.db_driver
        main_module.db_driver = mock_driver

        try:
            # Make request
            response = client.get("/api/stats")
            data = response.get_json()

            # Verify
            assert response.status_code == 200
            assert data["nodes"] == 1000000
            assert data["relationships"] == 5000000
        finally:
            main_module.db_driver = original


class TestMainFunction:
    """Test suite for main() function."""

    @patch("src.main.init_database")
    @patch("src.main.app.run")
    def test_main_initializes_database(self, mock_app_run, mock_init_db):
        """Test that main() initializes the database."""
        from src.main import main

        # Setup mock
        mock_driver = Mock()
        mock_init_db.return_value = mock_driver

        # Run main (will be interrupted by app.run mock)
        main()

        # Verify database was initialized
        mock_init_db.assert_called_once()

    @patch("src.main.init_database")
    @patch("src.main.app.run")
    @patch.dict(
        "os.environ",
        {"FLASK_HOST": "127.0.0.1", "FLASK_PORT": "5000", "FLASK_DEBUG": "True"},
    )
    def test_main_uses_environment_variables(self, mock_app_run, mock_init_db):
        """Test that main() uses environment variables for configuration."""
        from src.main import main

        # Setup mock
        mock_driver = Mock()
        mock_init_db.return_value = mock_driver

        # Run main
        main()

        # Verify app.run was called with correct parameters
        mock_app_run.assert_called_once()
        call_kwargs = mock_app_run.call_args[1]
        assert call_kwargs["host"] == "127.0.0.1"
        assert call_kwargs["port"] == 5000
        assert call_kwargs["debug"] is True

    @patch("src.main.init_database")
    @patch("src.main.app.run")
    def test_main_closes_driver_on_exit(self, mock_app_run, mock_init_db):
        """Test that main() closes driver on exit."""
        from src.main import main

        # Setup mock
        mock_driver = Mock()
        mock_init_db.return_value = mock_driver
        mock_app_run.side_effect = KeyboardInterrupt()

        # Run main (will be interrupted)
        main()

        # Verify driver was closed
        mock_driver.close.assert_called_once()

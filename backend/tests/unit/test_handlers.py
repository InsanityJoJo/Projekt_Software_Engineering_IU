"""Comprehensive tests for API handlers.

This module tests all handler functions with proper mocking
to achieve high test coverage.

andlers are initialized once in conftest.py app fixture.
Tests should NOT call handlers.init_handlers() again unless specifically
testing initialization logic.
"""

import pytest
from unittest.mock import Mock
from src.driver import ResultWrapper
from src.services.query_builder import QueryValidationError
from src.api import handlers


class TestHandlerInitialization:
    """Test handler initialization and dependency injection."""

    def test_init_handlers_with_driver_only(self):
        """Test initializing handlers with just a driver."""
        mock_driver = Mock()

        handlers.init_handlers(mock_driver)

        assert handlers.db_driver == mock_driver
        assert handlers.autocomplete_service is not None

    def test_init_handlers_with_autocomplete_service(self):
        """Test initializing handlers with both driver and autocomplete service."""
        mock_driver = Mock()
        mock_autocomplete = Mock()

        handlers.init_handlers(mock_driver, mock_autocomplete)

        assert handlers.db_driver == mock_driver
        assert handlers.autocomplete_service == mock_autocomplete


class TestHealthCheckHandler:
    """Test health check endpoint handler."""

    def test_health_check_success(self, client, mock_driver):
        """Test successful health check."""
        # Configure mock for this test
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"health": 1}]
        )

        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

    def test_health_check_database_unhealthy(self, client, mock_driver):
        """Test health check when database is disconnected."""
        # Configure mock for this test
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=False, error="Connection failed"
        )

        response = client.get("/api/health")
        assert response.status_code == 503

        data = response.get_json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"

    def test_health_check_driver_not_initialized(self, client):
        """Test health check when driver is not initialized."""

        handlers.db_driver = None

        response = client.get("/api/health")
        assert response.status_code == 503

        data = response.get_json()
        assert "Database driver not initialized" in data["error"]

    def test_health_check_exception_handling(self, client, mock_driver):
        """Test health check handles exceptions gracefully."""
        mock_driver.run_safe_query.side_effect = Exception("Database error")

        response = client.get("/api/health")
        assert response.status_code == 503

        data = response.get_json()
        assert data["status"] == "unhealthy"


class TestGetStatsHandler:
    """Test database statistics endpoint handler."""

    def test_get_stats_success(self, client, mock_driver):
        """Test successful stats retrieval."""
        mock_driver.run_safe_query.side_effect = [
            ResultWrapper(success=True, data=[{"count": 100}]),  # nodes
            ResultWrapper(success=True, data=[{"count": 250}]),  # relationships
        ]

        response = client.get("/api/stats")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert data["nodes"] == 100
        assert data["relationships"] == 250

    def test_get_stats_empty_database(self, client, mock_driver):
        """Test stats with empty database."""
        mock_driver.run_safe_query.side_effect = [
            ResultWrapper(success=True, data=[{"count": 0}]),
            ResultWrapper(success=True, data=[{"count": 0}]),
        ]

        response = client.get("/api/stats")
        assert response.status_code == 200

        data = response.get_json()
        assert data["nodes"] == 0
        assert data["relationships"] == 0

    def test_get_stats_node_query_fails(self, client, mock_driver):
        """Test stats when node query fails."""
        mock_driver.run_safe_query.side_effect = [
            ResultWrapper(success=False, error="Query failed"),
            ResultWrapper(success=True, data=[{"count": 250}]),
        ]

        response = client.get("/api/stats")
        assert response.status_code == 500

        data = response.get_json()
        assert data["success"] is False
        assert "Query failed" in data["error"]

    def test_get_stats_driver_not_initialized(self, client):
        """Test stats when driver not initialized."""
        handlers.db_driver = None

        response = client.get("/api/stats")
        assert response.status_code == 503


class TestExecuteQueryHandler:
    """Test Cypher query execution handler."""

    def test_execute_query_success(self, client, mock_driver):
        """Test successful query execution."""
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"name": "APT28"}, {"name": "APT29"}]
        )

        response = client.post(
            "/api/query",
            json={"query": "MATCH (n:ThreatActor) RETURN n", "parameters": {}},
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 2

    def test_execute_query_missing_query(self, client, mock_driver):
        """Test query execution without query field."""
        response = client.post("/api/query", json={"parameters": {}})
        assert response.status_code == 400

        data = response.get_json()
        assert "query" in data["error"].lower()

    def test_execute_query_with_parameters(self, client, mock_driver):
        """Test query execution with parameters."""
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"name": "APT28"}]
        )

        response = client.post(
            "/api/query",
            json={
                "query": "MATCH (n:ThreatActor {name: $name}) RETURN n",
                "parameters": {"name": "APT28"},
            },
        )
        assert response.status_code == 200

    def test_execute_query_invalid_json(self, client, mock_driver):
        """Test query execution with invalid JSON."""
        response = client.post(
            "/api/query",
            data="invalid json",
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_execute_query_empty_body(self, client, mock_driver):
        """Test query execution with empty request body."""
        response = client.post("/api/query", json=None)
        assert response.status_code == 400


class TestAutocompleteHandler:
    """Test autocomplete suggestion handler."""

    def test_autocomplete_success(self, client, mock_driver):
        """Test successful autocomplete."""
        handlers.autocomplete_service.suggest_node_names.return_value = ResultWrapper(
            success=True,
            data=[
                {"name": "ShadowGroup", "label": "ThreatActor", "id": "1"},
                {"name": "ShadowMalware", "label": "Malware", "id": "2"},
            ],
        )

        response = client.get("/api/autocomplete?q=Shad")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 2
        assert len(data["suggestions"]) == 2

    def test_autocomplete_min_length(self, client, mock_driver):
        """Test autocomplete with query less than 3 characters."""
        mock_autocomplete = Mock()
        handlers.init_handlers(mock_driver, mock_autocomplete)

        response = client.get("/api/autocomplete?q=Sh")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 0
        assert "Minimum 3 characters" in data["message"]

    def test_autocomplete_with_fuzzy_fallback(self, client, mock_driver):
        """Test autocomplete falls back to fuzzy search."""
        handlers.autocomplete_service.suggest_node_names.return_value = ResultWrapper(
            success=True, data=[{"name": "Shadow", "label": "ThreatActor", "id": "1"}]
        )
        handlers.autocomplete_service.fuzzy_search.return_value = ResultWrapper(
            success=True,
            data=[
                {"name": "DarkShadow", "label": "Campaign", "id": "2"},
                {"name": "ShadowNet", "label": "Tool", "id": "3"},
            ],
        )

        response = client.get("/api/autocomplete?q=Shad")
        assert response.status_code == 200

        data = response.get_json()
        assert data["count"] == 3  # 1 prefix + 2 fuzzy

    def test_autocomplete_with_label_filter(self, client, mock_driver):
        """Test autocomplete with label filter."""
        handlers.autocomplete_service.suggest_node_names.return_value = ResultWrapper(
            success=True, data=[{"name": "APT28", "label": "ThreatActor", "id": "1"}]
        )
        response = client.get("/api/autocomplete?q=APT&label=ThreatActor")
        assert response.status_code == 200

    def test_autocomplete_service_not_available(self, client, mock_driver):
        """Test autocomplete when service is not available."""
        handlers.autocomplete_service = None

        response = client.get("/api/autocomplete?q=test")
        assert response.status_code == 503


class TestGetNodesHandler:
    """Test get all nodes endpoint handler."""

    def test_get_nodes_success(self, client, mock_driver):
        """Test successful node retrieval."""
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True,
            data=[{"name": "APT28"}, {"name": "APT29"}],
        )

        response = client.get("/api/nodes")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 2

    def test_get_nodes_with_custom_limit(self, client, mock_driver):
        """Test node retrieval with custom limit."""
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"name": "APT28"}]
        )

        response = client.get("/api/nodes?limit=10")
        assert response.status_code == 200

    def test_get_nodes_with_label_filter(self, client, mock_driver):
        """Test node retrieval with label filter."""
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"name": "APT28"}]
        )

        response = client.get("/api/nodes?label=ThreatActor")
        assert response.status_code == 200

    def test_get_nodes_validation_error(self, client, mock_driver):
        """Test node retrieval with invalid label."""
        mock_driver.run_safe_query.side_effect = QueryValidationError("Invalid label")

        response = client.get("/api/nodes?label=InvalidLabel")
        assert response.status_code == 400


class TestCreateNodeHandler:
    """Test node creation endpoint handler."""

    def test_create_node_success(self, client, mock_driver):
        """Test successful node creation."""
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"name": "NewActor"}]
        )

        response = client.post(
            "/api/nodes",
            json={
                "label": "ThreatActor",
                "properties": {"name": "NewActor", "type": "APT"},
            },
        )
        assert response.status_code == 201

        data = response.get_json()
        assert data["success"] is True

    def test_create_node_missing_label(self, client, mock_driver):
        """Test node creation without label."""
        response = client.post("/api/nodes", json={"properties": {"name": "Test"}})
        assert response.status_code == 400

        data = response.get_json()
        assert "label" in data["error"].lower()

    def test_create_node_validation_error(self, client, mock_driver):
        """Test node creation with invalid label."""
        mock_driver.run_safe_query.side_effect = QueryValidationError("Invalid label")

        response = client.post(
            "/api/nodes",
            json={"label": "InvalidLabel", "properties": {}},
        )
        assert response.status_code == 400


class TestGetNodeByNameHandler:
    """Test get node by name endpoint handler."""

    def test_get_node_by_name_success(self, client, mock_driver):
        """Test successful node retrieval by name."""
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True,
            data=[
                {
                    "n": {"name": "APT28"},
                    "connections": [
                        {"relationship": "USES", "node": {"name": "X-Agent"}}
                    ],
                }
            ],
        )

        response = client.get("/api/node/APT28")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 1

    def test_get_node_by_name_not_found(self, client, mock_driver):
        """Test node retrieval when node doesn't exist."""
        mock_driver.run_safe_query.return_value = ResultWrapper(success=True, data=[])

        response = client.get("/api/node/NonExistent")
        assert response.status_code == 404

        data = response.get_json()
        assert data["success"] is False
        assert "not found" in data["error"]

    def test_get_node_by_name_with_label(self, client, mock_driver):
        """Test node retrieval with label filter."""
        mock_driver.run_safe_query.return_value = ResultWrapper(
            success=True, data=[{"n": {"name": "APT28"}, "connections": []}]
        )

        response = client.get("/api/node/APT28?label=ThreatActor")
        assert response.status_code == 200

    def test_get_node_by_name_validation_error(self, client, mock_driver):
        """Test node retrieval with invalid label."""
        mock_driver.run_safe_query.side_effect = QueryValidationError("Invalid label")

        response = client.get("/api/node/Test?label=InvalidLabel")
        assert response.status_code == 400

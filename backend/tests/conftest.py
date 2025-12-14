"""Pytest fixtures for Neo4j driver testing.

This module provides shared fixtures for testing the GraphDBDriver class.
It includes mocked Neo4j driver instances and common test data to ensure
consistent and isolated unit tests.
"""

import sys
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Make sure src is in path
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.driver import GraphDBDriver, ResultWrapper
from src.services.import_service import ImportService
from src.api import handlers

# ==============================================================================
# LEVEL 1: Database Component Mocks
# ==============================================================================
# These fixtures create the lowest-level mocks (database connections)


@pytest.fixture
def mock_neo4j_driver():
    """Provide a mocked Neo4j driver instance.

    This fixture creates a mock of the Neo4j GraphDatabase.driver,
    preventing actual database connections during unit tests.

    Use it when:
    - Testing GraphDBDriver class directly
    - You need to verify Neo4j driver methods are called correctly

    Dont use when:
    - Testing API handlers (use mock_driver instead)
    - Integration tests (use real database)

    Returns:
        MagicMock: A mocked Neo4j driver instance.

    Example:
        def test_driver_connection(mock_neo4j_driver):
            # mock_neo4j_driver is already patching Neo4j
            driver = GraphDBDriver("bolt://localhost", "user", "pass")
            assert driver is not None
    """
    with patch("src.driver.GraphDatabase.driver") as mock_driver:
        yield mock_driver


@pytest.fixture
def mock_session():
    """Provide a mocked Neo4j session.

    This fixture creates a mock session object that simulates the context
    manager behavior of a real Neo4j session. It includes mocked
    execute_read and execute_write methods.

    Returns:
        MagicMock: A mocked Neo4j session instance.
    """
    session = MagicMock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=False)
    return session


@pytest.fixture
def db_driver(mock_neo4j_driver, mock_session):
    """Provide a GraphDBDriver instance with mocked dependencies.

    This fixture creates a REAL GraphDBDriver instance, but with mocked
    Neo4j backend. This test uses GraphDBDriver's logic without needing
    a real database.

    FIXTURE DEPENDENCY CHAIN:
    mock_neo4j_driver → db_driver
    mock_session → db_driver

    Args:
        mock_neo4j_driver: The mocked Neo4j driver fixture.
        mock_session: The mocked session fixture.

    Returns:
        GraphDBDriver: A driver instance with mocked Neo4j backend.

    Example:
        def test_query_execution(db_driver):
            # db_driver is a real GraphDBDriver with mocked Neo4j
            result = db_driver.run_safe_query("MATCH (n) RETURN n")
            assert result is not None
    """
    mock_neo4j_driver.return_value.session.return_value = mock_session
    driver = GraphDBDriver(
        uri="bolt://localhost:7687", user="neo4j", password="password"
    )
    return driver


@pytest.fixture(scope="function")
def mock_driver():
    """Provide ONE mock_driver per test function.

    This fixture creates a properly configured mock driver with sensible
    defaults that return ResultWrapper objects with real data (not Mock objects).

    The key fix here is that run_safe_query returns ResultWrapper with REAL
    lists, not Mock objects, preventing "TypeError: 'Mock' object is not subscriptable".
    """
    driver = Mock()

    # Configure run_safe_query with a default that returns real data
    # Individual tests can override this with side_effect or return_value
    driver.run_safe_query.return_value = ResultWrapper(
        success=True,
        data=[]  # Real empty list, not Mock()
    )

    driver.execute = Mock(return_value=[])  # Real list
    driver.close = Mock()

    handlers.init_handlers(driver)

    # Patch autocomplete service with proper ResultWrapper responses
    # Access the PRIVATE variable through the module
    handlers._autocomplete_service = Mock()
    handlers._autocomplete_service.suggest_node_names.return_value = ResultWrapper(
        success=True, data=[{"name": "Alpha"}, {"name": "Beta"}]
    )
    handlers._autocomplete_service.fuzzy_search.return_value = ResultWrapper(
        success=True, data=[]
    )

    yield driver

    # Cleanup - reset private variables
    handlers._db_driver = None
    handlers._autocomplete_service = None


# ==============================================================================
# LEVEL 2: Application Setup
# ==============================================================================
# These fixtures create the Flask app and initialize it properly


@pytest.fixture
def app():
    """Create Flask app WITHOUT reinitializing handlers.

    Handlers are initialized by mock_driver fixture before app creates.
    """
    from flask import Flask
    from flask_cors import CORS

    test_app = Flask(__name__)
    CORS(test_app)
    test_app.config["TESTING"] = True

    # Register routes - handlers already initialized by mock_driver fixture
    from src.api.routes import api_bp

    test_app.register_blueprint(api_bp)

    return test_app


@pytest.fixture
def client(app, mock_driver):
    """Provide Flask test client.

    By depending on both app and mock_driver, we ensure:
    1. mock_driver creates and initializes handlers
    2. app creates with initialized handlers
    3. client uses app
    4. Test gets THE SAME mock_driver that handlers use
    """
    return app.test_client()


# ==============================================================================
# LEVEL 1: Query Result Mocks (Test Data)
# ==============================================================================
# These fixtures provide sample data for tests


@pytest.fixture
def sample_query_result():
    """Provide sample query result data.

    Returns data in the format that execute() now returns
    (list of dicts, not Mock objects).

    Returns:
        list: A list of dictionaries representing query results.
    """
    return [{"name": "Alice", "type": "Gang"}, {"name": "Bob", "type": "Gang"}]


@pytest.fixture
def empty_query_result():
    """Provide an empty query result.

    This fixture returns an empty list to simulate queries that return
    no results.

    Returns:
        list: An empty list.
    """
    return []


@pytest.fixture
def sample_cypher_query():
    """Provide a sample Cypher query string.

    Returns:
        str: A sample MATCH query.
    """
    return "MATCH (n:ThreatActor) RETURN n.name, n.type"


@pytest.fixture
def sample_query_params():
    """Provide sample query parameters.

    Returns:
        dict: A dictionary of sample parameters.
    """
    return {"name": "Alice", "type": "gang"}


# ==============================================================================
# LEVEL 2: ImportService Fixtures
# ==============================================================================


@pytest.fixture
def mock_import_driver():
    """Create a mock GraphDBDriver for ImportService tests.

    This is another driver mock, specifically for import service tests.
    - mock_driver: For handler tests
    - mock_import_driver: For import service tests

    Import service needs specific return values for its queries.
    """

    driver = Mock(spec=GraphDBDriver)
    driver.execute = Mock(return_value=[{"count": 1, "label": "TestLabel"}])
    driver.run_safe_query = Mock(return_value=ResultWrapper(success=True, data=[]))
    return driver


@pytest.fixture
def import_service(mock_import_driver):
    """Create an ImportService instance with mocked driver.

    FIXTURE DEPENDENCY CHAIN:
    mock_import_driver → import_service

    This creates a REAL ImportService, but with mocked database.
    Similar to db_driver pattern

    Args:
        mock_import_driver: The mocked driver fixture.

    Returns:
        ImportService: Service instance ready for testing.
    """
    return ImportService(mock_import_driver)


# ==============================================================================
# LEVEL 1: Test Data Fixtures
# ==============================================================================


@pytest.fixture
def valid_json_data():
    """Create valid JSON data for testing imports.

    Returns:
        dict: Valid threat intelligence data structure.
    """
    return {
        "metadata": {
            "version": "1.0",
            "source": "Test Source",
            "created": "2024-01-01T00:00:00Z",
            "description": "Test data",
        },
        "nodes": [
            {
                "label": "ThreatActor",
                "properties": {"name": "APT28", "type": "Nation-State"},
            },
            {
                "label": "Malware",
                "properties": {"name": "X-Agent", "family": "Sofacy"},
            },
        ],
        "relationships": [
            {
                "type": "USES",
                "from": {"label": "ThreatActor", "property": "name", "value": "APT28"},
                "to": {"label": "Malware", "property": "name", "value": "X-Agent"},
                "properties": {"source": "Report 1"},
            },
        ],
    }


@pytest.fixture
def temp_json_file(valid_json_data):
    """Create a temporary JSON file with test data.

    Creates a temporary file that is automatically cleaned up after the test.
    This ensures temporary files don't clutter system.

    Args:
        valid_json_data: The JSON data fixture.

    Yields:
        str: Path to the temporary JSON file.

    Example:
        def test_file_import(temp_json_file):
            # temp_json_file exists here
            data = load_json(temp_json_file)
            assert data is not None
            # After test completes, file is automatically deleted
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(valid_json_data, f)
        temp_path = f.name

    yield temp_path  # Test runs here

    # Cleanup after test
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def invalid_json_file():
    """Create a temporary file with invalid JSON.

    Yields:
        str: Path to the temporary file with invalid JSON.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{invalid json content")
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def sample_nodes():
    """Provide sample node data for testing.

    Returns:
        list: List of node dictionaries.
    """
    return [
        {
            "label": "ThreatActor",
            "properties": {"name": "APT28", "type": "Nation-State"},
        },
        {
            "label": "Malware",
            "properties": {"name": "X-Agent", "family": "Sofacy"},
        },
    ]


@pytest.fixture
def sample_relationships():
    """Provide sample relationship data for testing.

    Returns:
        list: List of relationship dictionaries.
    """
    return [
        {
            "type": "USES",
            "from": {"label": "ThreatActor", "property": "name", "value": "APT28"},
            "to": {"label": "Malware", "property": "name", "value": "X-Agent"},
            "properties": {"source": "Report 1"},
        },
    ]


@pytest.fixture
def large_dataset():
    """Create a large dataset for performance testing.

    Returns:
        dict: JSON data with 50 nodes and multiple relationships.
    """
    nodes = []

    # Create 50 nodes across multiple labels
    for i in range(20):
        nodes.append({"label": "ThreatActor", "properties": {"name": f"Actor{i}"}})
    for i in range(15):
        nodes.append({"label": "Malware", "properties": {"name": f"Malware{i}"}})
    for i in range(15):
        nodes.append({"label": "Tool", "properties": {"name": f"Tool{i}"}})

    return {
        "metadata": {"version": "1.0"},
        "nodes": nodes,
        "relationships": [],
    }

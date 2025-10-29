"""Pytest fixtures for Neo4j driver testing.

This module provides shared fixtures for testing the GraphDBDriver class.
It includes mocked Neo4j driver instances and common test data to ensure
consistent and isolated unit tests.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from src.driver import GraphDBDriver, ResultWrapper
from src.services.import_service import ImportService
from src.main import app


@pytest.fixture
def mock_neo4j_driver():
    """Provide a mocked Neo4j driver instance.

    This fixture creates a mock of the Neo4j GraphDatabase.driver,
    preventing actual database connections during unit tests. It returns
    a MagicMock that can be configured for specific test scenarios.

    Returns:
        MagicMock: A mocked Neo4j driver instance.
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

    This fixture creates a fully initialized GraphDBDriver instance with
    all Neo4j dependencies mocked. The driver is ready for testing without
    requiring an actual database connection.

    Args:
        mock_neo4j_driver: The mocked Neo4j driver fixture.
        mock_session: The mocked session fixture.

    Returns:
        GraphDBDriver: A driver instance with mocked Neo4j backend.
    """
    mock_neo4j_driver.return_value.session.return_value = mock_session
    driver = GraphDBDriver(
        uri="bolt://localhost:7687", user="neo4j", password="password"
    )
    return driver


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


# Flask API Fixtures


@pytest.fixture
def client():
    """Provide Flask test client.

    Returns:
        FlaskClient: Test client for making requests.
    """
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_driver():
    """Provide a mocked GraphDBDriver instance.

    Returns:
        Mock: Mocked driver with run_safe_query method.
    """
    driver = Mock()
    driver.run_safe_query = Mock()
    driver.execute = Mock()
    driver.close = Mock()
    return driver


# ImportService Fixtures


@pytest.fixture
def mock_import_driver():
    """Create a mock GraphDBDriver for ImportService tests.

    Returns:
        Mock: A mocked driver with execute method configured.
    """
    driver = Mock(spec=GraphDBDriver)
    driver.execute = Mock(return_value=[{"count": 1, "label": "TestLabel"}])
    return driver


@pytest.fixture
def import_service(mock_import_driver):
    """Create an ImportService instance with mocked driver.

    Args:
        mock_import_driver: The mocked driver fixture.

    Returns:
        ImportService: Service instance ready for testing.
    """
    return ImportService(mock_import_driver)


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

    Args:
        valid_json_data: The JSON data fixture.

    Yields:
        str: Path to the temporary JSON file.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(valid_json_data, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
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

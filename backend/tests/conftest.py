"""Pytest fixtures for Neo4j driver testing.

This module provides shared fixtures for testing the GraphDBDriver class.
It includes mocked Neo4j driver instances and common test data to ensure
consistent and isolated unit tests.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.driver import GraphDBDriver, ResultWrapper
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

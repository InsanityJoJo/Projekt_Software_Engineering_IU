"""Pytest fixtures for Neo4j driver testing.

This module provides shared fixtures for testing the GraphDBDriver class.
It includes mocked Neo4j driver instances and common test data to ensure
consistent and isolated unit tests.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.driver import GraphDBDriver, ResultWrapper


@pytest.fixture
def mock_neo4j_driver():
    """Provide a mocked Neo4j driver instance.

    This fixture creates a mock of the Neo4j GraphDatabase.driver,
    preventing actual database connections during unit tests. It returns
    a MagicMock that can be configured for specific test scenarios.

    Returns:
        MagicMock: A mocked Neo4j driver instance.
    """
    with patch("driver.GraphDatabase.driver") as mock_driver:
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

    This fixture returns a list of mock Neo4j record objects that simulate
    the structure of actual query results. Each record has a data() method
    that returns a dictionary.

    Returns:
        list: A list of mock Neo4j records.
    """
    mock_record1 = Mock()
    mock_record1.data.return_value = {"name": "Alice", "age": 30}

    mock_record2 = Mock()
    mock_record2.data.return_value = {"name": "Bob", "age": 25}

    return [mock_record1, mock_record2]


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
    return "MATCH (n:Person) RETURN n.name, n.age"


@pytest.fixture
def sample_query_params():
    """Provide sample query parameters.

    Returns:
        dict: A dictionary of sample parameters.
    """
    return {"name": "Alice", "age": 30}

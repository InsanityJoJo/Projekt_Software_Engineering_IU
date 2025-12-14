"""Unit tests for the Neo4j GraphDBDriver module.

This module contains comprehensive unit tests for the GraphDBDriver class
and ResultWrapper class. All tests use mocked Neo4j dependencies to ensure
fast, isolated testing without requiring a database connection.
"""

import pytest
import logging
from unittest.mock import Mock, MagicMock, patch, call
from src.driver import GraphDBDriver, ResultWrapper


class TestResultWrapper:
    """Test suite for the ResultWrapper class."""

    def test_init_success(self):
        """Test ResultWrapper initialization with success state."""
        data = [{"name": "Alice"}]
        wrapper = ResultWrapper(success=True, data=data)

        assert wrapper.success is True
        assert wrapper.data == data
        assert wrapper.error is None

    def test_init_failure(self):
        """Test ResultWrapper initialization with failure state."""
        error_msg = "Connection failed"
        wrapper = ResultWrapper(success=False, error=error_msg)

        assert wrapper.success is False
        assert wrapper.data is None
        assert wrapper.error == error_msg

    def test_bool_true(self):
        """Test ResultWrapper boolean evaluation when successful."""
        wrapper = ResultWrapper(success=True, data=[])
        assert bool(wrapper) is True

    def test_bool_false(self):
        """Test ResultWrapper boolean evaluation when failed."""
        wrapper = ResultWrapper(success=False, error="Error")
        assert bool(wrapper) is False

    def test_to_dict(self):
        """Test conversion of ResultWrapper to dictionary."""
        data = [{"id": 1}]
        error = "Some error"
        wrapper = ResultWrapper(success=True, data=data, error=error)

        result = wrapper.to_dict()

        assert result == {"success": True, "data": data, "error": error}

    def test_repr(self):
        """Test ResultWrapper string representation for debugging."""
        wrapper = ResultWrapper(success=True, data=["test"])
        repr_str = repr(wrapper)

        assert "ResultWrapper" in repr_str
        assert "success=True" in repr_str
        assert "data=['test']" in repr_str

    def test_str(self):
        """Test ResultWrapper JSON string representation."""
        wrapper = ResultWrapper(success=False, error="Test error")
        str_result = str(wrapper)

        assert '"success": false' in str_result
        assert '"error": "Test error"' in str_result


class TestGraphDBDriverInit:
    """Test suite for GraphDBDriver initialization."""

    def test_init_creates_driver(self, mock_neo4j_driver):
        """Test that initialization creates a Neo4j driver instance."""
        uri = "bolt://localhost:7687"
        user = "neo4j"
        password = "test_password"

        driver = GraphDBDriver(uri, user, password)

        mock_neo4j_driver.assert_called_once_with(uri, auth=(user, password))
        assert driver.driver is not None

    def test_init_sets_default_log_level(self, mock_neo4j_driver):
        """Test that initialization sets default logging level to INFO."""
        driver = GraphDBDriver("bolt://localhost", "user", "pass")

        assert driver.logger.level == logging.INFO

    def test_init_sets_custom_log_level(self, mock_neo4j_driver):
        """Test that initialization accepts custom logging level."""
        driver = GraphDBDriver(
            "bolt://localhost", "user", "pass", log_level=logging.DEBUG
        )

        assert driver.logger.level == logging.DEBUG


class TestGraphDBDriverConnect:
    """Test suite for GraphDBDriver connect method."""

    def test_connect_returns_connected(self, db_driver):
        """Test that connect method returns 'connected' string."""
        result = db_driver.connect()
        assert result == "connected"


class TestGraphDBDriverClose:
    """Test suite for GraphDBDriver close method."""

    def test_close_calls_driver_close(self, db_driver, mock_neo4j_driver):
        """Test that close method calls the underlying driver's close."""
        db_driver.close()

        db_driver.driver.close.assert_called_once()

    def test_close_logs_message(self, db_driver):
        """Test that close method logs an info message."""
        with patch.object(db_driver.logger, "info") as mock_log:
            db_driver.close()
            mock_log.assert_called_with("Neo4j driver closed.")


class TestGraphDBDriverExecute:
    """Test suite for GraphDBDriver execute method."""

    def test_execute_read_query_success(
        self, db_driver, mock_session, sample_query_result, sample_cypher_query
    ):
        """Test successful execution of a read query."""
        mock_session.execute_read.return_value = sample_query_result

        result = db_driver.execute(sample_cypher_query)

        assert len(result) == 2
        assert result[0] == {"name": "Alice", "type": "Gang"}
        assert result[1] == {"name": "Bob", "type": "Gang"}
        mock_session.execute_read.assert_called_once()

    def test_execute_write_query_success(
        self, db_driver, mock_session, sample_query_result
    ):
        """Test successful execution of a write query."""
        query = "CREATE (n:ThreatActor {name: $name})"
        params = {"name": "Charlie"}
        mock_session.execute_write.return_value = sample_query_result

        result = db_driver.execute(query, params, write=True)

        assert len(result) == 2
        mock_session.execute_write.assert_called_once()

    def test_execute_with_parameters(
        self, db_driver, mock_session, sample_query_result, sample_query_params
    ):
        """Test execute method with query parameters."""
        query = "MATCH (n:ThreatActor {name: $name}) RETURN n"
        mock_session.execute_read.return_value = sample_query_result

        result = db_driver.execute(query, sample_query_params)

        assert result is not None
        mock_session.execute_read.assert_called_once()

    def test_execute_without_parameters(
        self, db_driver, mock_session, sample_query_result
    ):
        """Test execute method without parameters."""
        query = "MATCH (n:ThreatActor) RETURN n"
        mock_session.execute_read.return_value = sample_query_result

        result = db_driver.execute(query)

        assert result is not None

    def test_execute_empty_result(self, db_driver, mock_session, empty_query_result):
        """Test execute method with empty query result."""
        query = "MATCH (n:NonExistent) RETURN n"
        mock_session.execute_read.return_value = empty_query_result

        result = db_driver.execute(query)

        assert result == []

    def test_execute_logs_read_operation(
        self, db_driver, mock_session, sample_query_result
    ):
        """Test that execute logs read operations."""
        query = "MATCH (n) RETURN n"
        params = {"test": "value"}
        mock_session.execute_read.return_value = sample_query_result

        with patch.object(db_driver.logger, "info") as mock_log:
            db_driver.execute(query, params)

            calls = mock_log.call_args_list
            assert any("Read query executed" in str(c) for c in calls)

    def test_execute_logs_write_operation(
        self, db_driver, mock_session, sample_query_result
    ):
        """Test that execute logs write operations."""
        query = "CREATE (n:Test)"
        mock_session.execute_write.return_value = sample_query_result

        with patch.object(db_driver.logger, "info") as mock_log:
            db_driver.execute(query, write=True)

            calls = mock_log.call_args_list
            assert any("Write query executed" in str(c) for c in calls)

    def test_execute_raises_runtime_error_on_failure(self, db_driver, mock_session):
        """Test that execute raises RuntimeError on query failure."""
        query = "INVALID CYPHER"
        mock_session.execute_read.side_effect = Exception("Syntax error")

        with pytest.raises(RuntimeError) as exc_info:
            db_driver.execute(query)

        assert "Query failed" in str(exc_info.value)
        assert query in str(exc_info.value)

    def test_execute_logs_error_on_failure(self, db_driver, mock_session):
        """Test that execute logs errors when query fails."""
        query = "INVALID CYPHER"
        error_msg = "Syntax error"
        mock_session.execute_read.side_effect = Exception(error_msg)

        with patch.object(db_driver.logger, "error") as mock_log:
            with pytest.raises(RuntimeError):
                db_driver.execute(query)

            mock_log.assert_called_once()
            assert error_msg in str(mock_log.call_args)


class TestGraphDBDriverRunSafeQuery:
    """Test suite for GraphDBDriver run_safe_query method."""

    def test_run_safe_query_success(self, db_driver, mock_session, sample_query_result):
        """Test run_safe_query returns ResultWrapper on success."""
        query = "MATCH (n) RETURN n"
        mock_session.execute_read.return_value = sample_query_result

        result = db_driver.run_safe_query(query)

        assert isinstance(result, ResultWrapper)
        assert result.success is True
        assert len(result.data) == 2
        assert result.error is None

    def test_run_safe_query_with_parameters(
        self, db_driver, mock_session, sample_query_result, sample_query_params
    ):
        """Test run_safe_query with query parameters."""
        query = "MATCH (n:ThreatActor {name: $name}) RETURN n"
        mock_session.execute_read.return_value = sample_query_result

        result = db_driver.run_safe_query(query, sample_query_params)

        assert result.success is True
        assert result.data is not None

    def test_run_safe_query_handles_exception(self, db_driver, mock_session):
        """Test run_safe_query catches exceptions and returns ResultWrapper."""
        query = "INVALID CYPHER"
        error_msg = "Syntax error"
        mock_session.execute_read.side_effect = Exception(error_msg)

        result = db_driver.run_safe_query(query)

        assert isinstance(result, ResultWrapper)
        assert result.success is False
        assert result.data is None
        assert error_msg in result.error

    def test_run_safe_query_does_not_raise_exception(self, db_driver, mock_session):
        """Test that run_safe_query never raises exceptions."""
        query = "INVALID CYPHER"
        mock_session.execute_read.side_effect = Exception("Error")

        # Should not raise any exception
        result = db_driver.run_safe_query(query)
        assert not result.success

    def test_run_safe_query_logs_error_on_failure(self, db_driver, mock_session):
        """Test that run_safe_query logs errors on failure.

        Note: Only execute() logs at ERROR level. run_safe_query() logs
        at DEBUG level to avoid duplicate error logs.
        """
        query = "INVALID"
        error_msg = "Test error"
        mock_session.execute_read.side_effect = Exception(error_msg)

        with patch.object(db_driver.logger, "error") as mock_error_log:
            with patch.object(db_driver.logger, "debug") as mock_debug_log:
                db_driver.run_safe_query(query)

                # execute() logs at ERROR level
                assert mock_error_log.call_count == 1
                assert error_msg in str(mock_error_log.call_args)

                # run_safe_query() logs at DEBUG level
                assert mock_debug_log.call_count == 1
                assert "Safe query wrapper caught RuntimeError" in str(
                    mock_debug_log.call_args
                )

    def test_run_safe_query_boolean_evaluation_success(
        self, db_driver, mock_session, sample_query_result
    ):
        """Test that successful ResultWrapper evaluates to True."""
        query = "MATCH (n) RETURN n"
        mock_session.execute_read.return_value = sample_query_result

        result = db_driver.run_safe_query(query)

        if result:
            assert True
        else:
            pytest.fail("ResultWrapper should evaluate to True")

    def test_run_safe_query_boolean_evaluation_failure(self, db_driver, mock_session):
        """Test that failed ResultWrapper evaluates to False."""
        query = "INVALID"
        mock_session.execute_read.side_effect = Exception("Error")

        result = db_driver.run_safe_query(query)

        if not result:
            assert True
        else:
            pytest.fail("ResultWrapper should evaluate to False")


class TestGraphDBDriverSessionManagement:
    """Test suite for session management in GraphDBDriver."""

    def test_execute_opens_and_closes_session(
        self, db_driver, mock_session, sample_query_result
    ):
        """Test that execute properly opens and closes session."""
        query = "MATCH (n) RETURN n"
        mock_session.execute_read.return_value = sample_query_result

        db_driver.execute(query)

        mock_session.__enter__.assert_called_once()
        mock_session.__exit__.assert_called_once()

    def test_execute_closes_session_on_error(self, db_driver, mock_session):
        """Test that session closes even when query fails."""
        query = "INVALID"
        mock_session.execute_read.side_effect = Exception("Error")

        with pytest.raises(RuntimeError):
            db_driver.execute(query)

        mock_session.__exit__.assert_called_once()

"""Neo4j database driver module.

This module provides a wrapper around the Neo4j Python driver for
managing database connections and executing Cypher queries. It includes
error handling, logging, and a standardized result wrapper for consistent
query result handling.
"""

import json
import logging
from typing import Any, Optional

from neo4j import GraphDatabase

from src.logger import setup_logger


class ResultWrapper:
    """Encapsulate the outcome of a database operation.

    This class provides a standardized container for query results.
    It indicates whether the operation succeeded, and contains
    the associated data or error message. It can be used to ensure
    consistent handling of results across different driver methods.

    Attributes:
        success (bool): Indicates whether the operation was successful.
        data (Any): The query result data, if available.
        error (Optional[str]): The error message, if an exception occurred.
    """

    def __init__(self, success: bool, data: Any = None, error: Optional[str] = None):
        """Initialize a ResultWrapper instance.

        Args:
            success: Whether the operation succeeded.
            data: The result data from the query. Defaults to None.
            error: Error message if operation failed. Defaults to None.
        """
        self.success = success
        self.data = data
        self.error = error

    def __bool__(self) -> bool:
        """Return the success flag when evaluated in a boolean context.

        Returns:
            bool: True if operation was successful, False otherwise.
        """
        return self.success

    def to_dict(self) -> dict[str, Any]:
        """Convert the result wrapper to a dictionary.

        Returns:
            dict: Dictionary containing success, data, and error fields.
        """
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }

    def __repr__(self) -> str:
        """Return a string representation for debugging.

        Returns:
            str: Debug string showing all attributes.
        """
        return (
            f"ResultWrapper(success={self.success}, "
            f"data={self.data}, error={self.error})"
        )

    def __str__(self) -> str:
        """Return a JSON-formatted string representation of the result.

        Returns:
            str: JSON string of the result dictionary.
        """
        return json.dumps(self.to_dict(), indent=2)


class GraphDBDriver:
    """Wrapper for Neo4j database driver with enhanced logging and error handling.

    This class manages connections to a Neo4j database and provides methods
    for executing Cypher queries safely. It includes comprehensive logging
    and standardized error handling through the ResultWrapper class.

    Attributes:
        driver: The underlying Neo4j driver instance.
        logger: Logger instance for this driver.
    """

    def __init__(
        self, uri: str, user: str, password: str, log_level: int = logging.INFO
    ):
        """Initialize the GraphDBDriver with connection parameters.

        Args:
            uri: The Neo4j connection URI (e.g., 'bolt://localhost:7687').
            user: Database username for authentication.
            password: Database password for authentication.
            log_level: Logging level for this driver. Defaults to logging.INFO.
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.logger = setup_logger("GraphDBDriver", log_level)
        self.logger.info("Neo4j driver initialized.")

    def connect(self) -> str:
        """Verify connection to the database.

        Note: This is a placeholder method. Consider implementing actual
        connection verification in future versions.

        Returns:
            str: Connection status message.
        """
        return "connected"

    def close(self) -> None:
        """Close the connection to the database.

        This method should be called when the driver is no longer needed
        to properly release database resources.
        """
        self.driver.close()
        self.logger.info("Neo4j driver closed.")

    def execute(
        self, query: str, parameters: Optional[dict] = None, write: bool = False
    ) -> list[dict]:
        """Execute a Cypher query and return raw result data.

        This method runs the given Cypher query against the Neo4j database
        using the active driver session. It automatically manages session
        lifecycle and returns the raw query results as a list of dictionaries
        (one per record). On failure, it raises a RuntimeError with detailed
        information about the query and parameters.

        Args:
            query: The Cypher query to execute.
            parameters: Query parameters for parameterized queries.
                Defaults to None.
            write: Whether this is a write operation. If True, uses
                execute_write for transactional guarantees. Defaults to False.

        Returns:
            list[dict]: The result records as dictionaries.

        Raises:
            RuntimeError: If the query execution fails, with details about
                the query, parameters, and underlying exception.
        """

        def _execute_query(tx):
            """Execute query within transaction and consume results."""
            result = tx.run(query, parameters or {})
            # CRITICAL: Consume results INSIDE the transaction
            return [record.data() for record in result]

        try:
            # Open session using context manager for automatic cleanup
            with self.driver.session() as session:
                # Use appropriate transaction function based on operation type
                if write:
                    data = session.execute_write(_execute_query)
                    self.logger.info("Write query executed: %s with params: %s", query, parameters)
                else:
                    data = session.execute_read(_execute_query)
                    self.logger.info("Read query executed: %s with params: %s", query, parameters)

                self.logger.debug("Query returned %d records", len(data))

                return data

        except Exception as e:
            self.logger.error("Query execution failed: %s", e)
            raise RuntimeError(
                f"Query failed: {e}\nQuery: {query}\nParams: {parameters}"
            ) from e

    def run_safe_query(
        self, query: str, parameters: Optional[dict] = None
    ) -> ResultWrapper:
        """Execute a Cypher query safely and return a standardized result object.

        This method wraps the `execute` call in a try/except block and returns
        a `ResultWrapper` object containing a success flag, data (if available),
        and an error message on failure. It prevents exceptions from propagating
        to the caller, making it suitable for batch jobs, GUIs, or APIs where
        graceful error handling is required.

        Note: This method only supports read operations. For write operations,
        use the execute() method directly.

        Args:
            query: The Cypher query to execute.
            parameters: Query parameters for parameterized queries.
                Defaults to None.

        Returns:
            ResultWrapper: An object containing success status, data, and
                error info. Use the boolean evaluation or .success attribute
                to check if the operation succeeded.
        """
        try:
            data = self.execute(query, parameters)
            return ResultWrapper(success=True, data=data)

        except RuntimeError as e:
            # Expected: execute() raises RuntimeError on query failures
            # (execute() already logged the error)
            self.logger.debug("Safe query wrapper caught RuntimeError: %s", str(e))
            return ResultWrapper(success=False, error=str(e))

        except Exception as e:
            # Unexpected: This shouldn't happen but catch it anyway
            # since this is a "safe" wrapper
            self.logger.exception("Unexpected error in run_safe_query")
            return ResultWrapper(success=False, error=f"Unexpected error: {str(e)}")

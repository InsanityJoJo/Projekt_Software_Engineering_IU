"""Main backend entry point.

Simplified main.py that just initializes the application.
All routes are in api/routes.py, all logic is in api/handlers.py.
"""

import logging
import os
import sys

from flask import Flask
from flask_cors import CORS
from neo4j.exceptions import AuthError, Neo4jError, ServiceUnavailable

from src.driver import GraphDBDriver
from src.logger import setup_logger

# Initialize Flask
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Initialize logger
logger = setup_logger("API", logging.INFO)

# Global database driver
DB_DRIVER = None


def init_database() -> GraphDBDriver:
    """Initialize database connection with environmental variables.

    Returns:
        GraphDBDriver: Initialized driver instance.

    Raises:
        SystemExit: If connection fails.
    """
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper())

    logger.info("Connecting to Neo4j at %s", neo4j_uri)

    try:
        driver = GraphDBDriver(
            uri=neo4j_uri, user=neo4j_user, password=neo4j_password, log_level=log_level
        )
        # Test connection
        result = driver.run_safe_query("RETURN 1 AS test")
        if not result.success:
            raise RuntimeError(f"Connection test failed: {result.error}")
        logger.info("Database connection established")
        return driver

    except AuthError as e:
        logger.error("Authentication failed: %s", e)
        logger.error("Check NEO4J_USER and NEO4J_PASSWORD environment variables")
        sys.exit(1)

    except ServiceUnavailable as e:
        logger.error("Neo4j service unavailable: %s", e)
        logger.error("Check NEO4J_URI and ensure Neo4j is running")
        sys.exit(1)

    except Neo4jError as e:
        logger.error("Neo4j error: %s", e)
        sys.exit(1)

    except RuntimeError as e:
        logger.error("Connection test failed: %s", e)
        sys.exit(1)

    except Exception as e:
        logger.exception("Unexpected error during database initialization")
        sys.exit(1)

def main():
    """Initialize and run the Flask application."""
    global DB_DRIVER

    print("=" * 60)
    print("Starting Flask Backend API")
    print("=" * 60)

    # Initialize database
    DB_DRIVER = init_database()

    # Import here to avoid circular dependencies and ensure proper initialization order
    from src.api import handlers  # pylint: disable=import-outside-toplevel

    handlers.init_handlers(DB_DRIVER)

    # Register routes blueprint
    from src.api.routes import api_bp

    app.register_blueprint(api_bp)

    # Get configuration
    host = os.getenv("FLASK_HOST", "0.0.0.0")

    # port is int but getenv returns string,
    try:
        port = int(os.getenv("FLASK_PORT", "8000"))
    except ValueError:
        logger.warning("Invalid FLASK_PORT, using default 8000")
        port = 8000
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    print(f"API running at: http://{host}:{port}")
    print(f"Health check: http://{host}:{port}/api/health")
    print(f"Debug mode: {debug}")
    print("=" * 60)

    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
    finally:
        if DB_DRIVER:
            DB_DRIVER.close()
            logger.info("Database connection closed")
        print("Goodbye!")


if __name__ == "__main__":
    main()

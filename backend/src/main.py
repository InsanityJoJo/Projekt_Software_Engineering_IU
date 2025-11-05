"""Main backend entry point.

Simplified main.py that just initializes the application.
All routes are in api/routes.py, all logic is in api/handlers.py.
"""

import os
import sys
import logging
from src.driver import GraphDBDriver
from src.logger import setup_logger
from flask import Flask
from flask_cors import CORS

# Initialize Flask
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Initialize logger
logger = setup_logger("API", logging.INFO)

# Global database driver
db_driver = None


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

    logger.info(f"Connecting to Neo4j at {neo4j_uri}")

    try:
        driver = GraphDBDriver(
            uri=neo4j_uri, user=neo4j_user, password=neo4j_password, log_level=log_level
        )

        # Test connection
        result = driver.run_safe_query("RETURN 1 AS test")
        if not result.success:
            raise Exception(f"Connection test failed: {result.error}")

        logger.info("Database connection established")
        return driver

    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)


def main():
    """Initialize and run the Flask application."""
    global db_driver

    print("=" * 60)
    print("Starting Flask Backend API")
    print("=" * 60)

    # Initialize database
    db_driver = init_database()

    # Initialize handlers with dependencies
    from src.api import handlers

    handlers.init_handlers(db_driver)

    # Register routes blueprint
    from src.api.routes import api_bp

    app.register_blueprint(api_bp)

    # Get configuration
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 8000))
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
        if db_driver:
            db_driver.close()
            logger.info("Database connection closed")
        print("Goodbye!")


if __name__ == "__main__":
    main()

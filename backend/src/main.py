"""Main backend entry point.

This module provides a REST API for the Svelte frontend to interact with the Neo4j Database.
It receives JSON requests, builds Cypher queries, executes them, and returns JSON responses.
"""

import os
import sys
import logging
from typing import Optional
from driver import GraphDBDriver
from logger import setup_logger
from flask import Flask, request, jsonify
from flask_cors import CORS


# Initialize Flask
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Initialize logger
logger = setup_logger("API", logging.INFO)

# Global database driver, declare type (initialized in main() method)
db_driver: Optional[GraphDBDriver] = None


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


# ============================================================================
# API Routes
# ============================================================================


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint.

    Returns:
        JSON: Service health status.
    """

    try:
        assert db_driver is not None, "Database not initialized"
        result = db_driver.run_safe_query("RETURN 1 AS health")
        db_healthy = result.success
    except:
        db_healthy = False

    return jsonify(
        {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
        }
    ), 200 if db_healthy else 503


@app.route("/api/query", methods=["POST"])
def execute_query():
    """Execute a Cypher query.

    Request JSON:
        {
            "query": "MATCH (n) RETURN n LIMIT 10",
            "parameters": {"optional": "params"}
        }

    Returns:
        JSON: Query results or error message.
    """
    try:
        data = request.get_json()

        if not data or "query" not in data:
            return jsonify({"error": "Query required"}), 400

        query = data["query"]
        parameters = data.get("parameters", None)

        logger.info(f"Executing query: {query[:100]}...")

        result = db_driver.run_safe_query(query, parameters)

        if result.success:
            return jsonify(
                {"success": True, "data": result.data, "count": len(result.data)}
            ), 200
        else:
            return jsonify({"success": False, "error": result.error}), 400

    except Exception as e:
        logger.error(f"Query execution error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/nodes", methods=["GET"])
def get_nodes():
    """Get all nodes from database.

    Query Parameters:
        limit (int): Maximum number of nodes to return (default: 100)

    Returns:
        JSON: List of nodes.
    """
    try:
        limit = request.args.get("limit", 100, type=int)

        query = "MATCH (n) RETURN n LIMIT $limit"
        result = db_driver.run_safe_query(query, {"limit": limit})

        if result.success:
            return jsonify(
                {"success": True, "nodes": result.data, "count": len(result.data)}
            ), 200
        else:
            return jsonify({"success": False, "error": result.error}), 500

    except Exception as e:
        logger.error(f"Error fetching nodes: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/nodes", methods=["POST"])
def create_node():
    """Create a new node.

    Request JSON:
        {
            "label": "Person",
            "properties": {
                "name": "Alice",
                "age": 30
            }
        }

    Returns:
        JSON: Created node information.
    """
    try:
        data = request.get_json()

        if not data or "label" not in data:
            return jsonify({"error": "Label required"}), 400

        label = data["label"]
        properties = data.get("properties", {})

        # Build property string for Cypher
        prop_strings = [f"{key}: ${key}" for key in properties.keys()]
        prop_clause = "{" + ", ".join(prop_strings) + "}" if prop_strings else ""

        query = f"CREATE (n:{label} {prop_clause}) RETURN n"

        result = db_driver.execute(query, properties, write=True)

        return jsonify(
            {
                "success": True,
                "data": result,
                "message": f"Node created with label {label}",
            }
        ), 201

    except Exception as e:
        logger.error(f"Error creating node: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get database statistics.

    Returns:
        JSON: Database statistics (node count, relationship count, etc.)
    """
    try:
        node_query = "MATCH (n) RETURN count(n) AS count"
        rel_query = "MATCH ()-[r]->() RETURN count(r) AS count"

        node_result = db_driver.run_safe_query(node_query)
        rel_result = db_driver.run_safe_query(rel_query)

        if node_result.success and rel_result.success:
            return jsonify(
                {
                    "success": True,
                    "nodes": node_result.data[0]["count"],
                    "relationships": rel_result.data[0]["count"],
                }
            ), 200
        else:
            error = node_result.error or rel_result.error
            return jsonify({"success": False, "error": error}), 500

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Application Entry Point
# ============================================================================


def main():
    """Initialize and run the Flask application."""
    global db_driver

    print("=" * 60)
    print("Starting Flask Backend API")
    print("=" * 60)

    # Initialize database
    db_driver = init_database()

    # Get configuration
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 8000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    print(f"API running at: http://{host}:{port}")
    print(f"Health check: http://{host}:{port}/health")
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

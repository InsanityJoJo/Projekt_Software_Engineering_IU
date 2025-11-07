"""API Handlers - Request handling and business logic.

FIXED: handle_get_node_by_name now properly fetches nodes with correct queries.
"""

from flask import jsonify, request
from werkzeug.exceptions import BadRequest, UnsupportedMediaType
from src.logger import setup_logger
from src.services.autocomplete_service import AutocompleteService
from src.services.query_builder import QueryValidationError, SafeQueryBuilder

# Initialize logger
logger = setup_logger("Handlers", "INFO")

# Service instances (will be injected from main.py)
db_driver = None
autocomplete_service = None


def init_handlers(driver, autocomplete_svc=None):
    """Initialize handlers with dependencies.

    Args:
        driver: GraphDBDriver instance
        autocomplete_svc: AutocompleteService instance (optional)
    """
    global db_driver, autocomplete_service
    db_driver = driver

    if autocomplete_svc:
        autocomplete_service = autocomplete_svc
    else:
        # Create autocomplete service if not provided
        autocomplete_service = AutocompleteService(driver)


# Health & Status Handlers
def handle_health_check():
    """Handle health check request."""
    try:
        if db_driver is None:
            return jsonify(
                {"status": "unhealthy", "error": "Database driver not initialized"}
            ), 503

        result = db_driver.run_safe_query("RETURN 1 AS health")

        if result.success:
            return jsonify({"status": "healthy", "database": "connected"}), 200
        else:
            return jsonify(
                {
                    "status": "unhealthy",
                    "database": "disconnected",
                    "error": result.error,
                }
            ), 503

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503


def handle_get_stats():
    """Handle get statistics request."""
    try:
        if db_driver is None:
            return jsonify({"error": "Database not initialized"}), 503

        builder = SafeQueryBuilder()

        node_query, node_params = builder.count_nodes()
        node_result = db_driver.run_safe_query(node_query, node_params)

        rel_query, rel_params = builder.count_relationships()
        rel_result = db_driver.run_safe_query(rel_query, rel_params)

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
            logger.error(f"Stats query failed: {error}")
            return jsonify({"success": False, "error": error}), 500

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


# Query Handlers
def handle_execute_query(request):
    """Handle Cypher query execution."""
    try:
        if db_driver is None:
            return jsonify({"error": "Database not initialized"}), 503

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

    except (BadRequest, UnsupportedMediaType) as e:
        logger.warning(f"Bad request: {e}")
        return jsonify({"error": "Invalid JSON format"}), 400

    except Exception as e:
        logger.error(f"Query execution error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


def handle_autocomplete(request):
    """Handle autocomplete request."""
    try:
        if autocomplete_service is None:
            return jsonify(
                {"success": False, "error": "Autocomplete service not available"}
            ), 503

        query = request.args.get("q", "").strip()
        label = request.args.get("label", None)
        limit = min(int(request.args.get("limit", 10)), 20)

        if len(query) < 3:
            return jsonify(
                {
                    "success": True,
                    "suggestions": [],
                    "count": 0,
                    "message": "Minimum 3 characters required",
                }
            ), 200

        # Try prefix match first
        result = autocomplete_service.suggest_node_names(
            prefix=query, label=label, limit=limit
        )

        # If fewer than 3 results, try fuzzy search
        if result.success and isinstance(result.data, list) and len(result.data) < 3:
            fuzzy_result = autocomplete_service.fuzzy_search(
                search_term=query, label=label, limit=limit
            )
            if fuzzy_result.success:
                # Merge and deduplicate
                seen = {item["name"] for item in result.data}
                for item in fuzzy_result.data:
                    if item["name"] not in seen:
                        result.data.append(item)
                        seen.add(item["name"])

        if result.success:
            return jsonify(
                {
                    "success": True,
                    "suggestions": result.data[:limit],
                    "count": len(result.data[:limit]),
                }
            ), 200
        else:
            return jsonify({"success": False, "error": result.error}), 500

    except ValueError as e:
        return jsonify({"success": False, "error": f"Invalid parameter: {str(e)}"}), 400

    except Exception as e:
        logger.error(f"Autocomplete error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


# Node Handlers
def handle_get_nodes(request):
    """Handle get all nodes request."""
    try:
        if db_driver is None:
            return jsonify({"error": "Database not initialized"}), 503

        limit = request.args.get("limit", 100, type=int)
        label = request.args.get("label", None)

        builder = SafeQueryBuilder()

        try:
            query, params = builder.get_all_nodes(label=label, limit=limit)
            result = db_driver.run_safe_query(query, params)

            if result.success:
                return jsonify(
                    {"success": True, "nodes": result.data, "count": len(result.data)}
                ), 200
            else:
                logger.error(f"Get nodes query failed: {result.error}")
                return jsonify({"success": False, "error": result.error}), 500

        except QueryValidationError as e:
            logger.warning(f"Validation error: {e}")
            return jsonify({"error": str(e)}), 400

    except Exception as e:
        logger.error(f"Error fetching nodes: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


def handle_create_node(request):
    """Handle create node request.

    IMPORTANT: Should be restricted to authenticated admin users!
    """
    try:
        if db_driver is None:
            return jsonify({"error": "Database not initialized"}), 503

        data = request.get_json()

        if not data or "label" not in data:
            return jsonify({"error": "Label required"}), 400

        label = data["label"]
        properties = data.get("properties", {})

        from src.services.query_builder import AdminQueryBuilder

        admin_builder = AdminQueryBuilder()

        try:
            query, params = admin_builder.merge_node(
                label=label,
                set_properties=properties,
                match_properties={"name": properties["name"]}
                if "name" in properties
                else {},
            )

            result = db_driver.run_safe_query(query, params)

            if result.success:
                return jsonify(
                    {
                        "success": True,
                        "data": result.data,
                        "message": f"Node created with label {label}",
                    }
                ), 201
            else:
                return jsonify({"success": False, "error": result.error}), 500

        except QueryValidationError as e:
            logger.warning(f"Validation error: {e}")
            return jsonify({"error": str(e)}), 400

    except (BadRequest, UnsupportedMediaType) as e:
        logger.warning(f"Bad request: {e}")
        return jsonify({"error": "Invalid JSON format"}), 400

    except Exception as e:
        logger.error(f"Error creating node: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


def handle_get_node_by_name(name, request):
    """Handle get node by name request.

    Uses SafeQueryBuilder for secure, validated query construction.

    Args:
        name: Node name to search for (exact match, case-sensitive)
        request: Flask request object

    Returns:
        JSON response with node details and relationships
    """
    try:
        if db_driver is None:
            return jsonify({"error": "Database not initialized"}), 503

        # Get optional label filter
        label = request.args.get("label", None)

        logger.info(f"Fetching node: name='{name}', label={label}")

        # Use query builder for safe, validated query
        builder = SafeQueryBuilder()

        try:
            query, params = builder.get_node_with_relationships(
                property_name="name",
                property_value=name,
                label=label,
                include_metadata=True,
                limit=1,
            )
        except QueryValidationError as e:
            # Validation errors return 400 Bad Request
            logger.warning(f"Validation error: {e}")
            return jsonify({"error": str(e)}), 400

        # Execute query
        result = db_driver.run_safe_query(query, params)

        if result.success:
            if len(result.data) == 0:
                logger.warning(f"Node not found: '{name}' (label={label})")
                return jsonify(
                    {"success": False, "error": f"Node '{name}' not found"}
                ), 404

            logger.info(f"Node found: '{name}', returning {len(result.data)} result(s)")

            return jsonify(
                {"success": True, "data": result.data, "count": len(result.data)}
            ), 200
        else:
            logger.error(f"Get node query failed: {result.error}")
            return jsonify({"success": False, "error": result.error}), 500

    except Exception as e:
        logger.error(f"Get node error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500

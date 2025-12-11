"""API Handlers - Request handling and business logic.

This module contains all business logic for API endpoints.
All handlers use SafeQueryBuilder and AdminQueryBuilder - no raw Cypher.
"""

from flask import jsonify
from neo4j.exceptions import Neo4jError
from werkzeug.exceptions import BadRequest, UnsupportedMediaType

from src.logger import setup_logger
from src.services.autocomplete_service import AutocompleteService
from src.services.query_builder import QueryValidationError, SafeQueryBuilder

logger = setup_logger("Handlers", 10)

_db_driver = None
_autocomplete_service = None


def init_handlers(driver, autocomplete_svc=None):
    """Initialize handlers with dependencies.

    Args:
        driver: GraphDBDriver instance
        autocomplete_svc: AutocompleteService instance (optional)
    """
    global _db_driver, _autocomplete_service
    _db_driver = driver

    if autocomplete_svc:
        _autocomplete_service = autocomplete_svc
    else:
        _autocomplete_service = AutocompleteService(driver)


def handle_health_check():
    """Handle health check request."""
    try:
        if _db_driver is None:
            return jsonify(
                {"status": "unhealthy", "error": "Database driver not initialized"}
            ), 503

        result = _db_driver.run_safe_query("RETURN 1 AS health")

        if result.success:
            return jsonify({"status": "healthy", "database": "connected"}), 200
        return jsonify(
            {
                "status": "unhealthy",
                "database": "disconnected",
                "error": result.error,
             }
         ), 503

    except Neo4jError as e:
        logger.error("Database error in health check: %s", e)
        return jsonify({"status": "unhealthy", "error": "Database error"}), 503

    except Exception:
        logger.exception("Unexpected error in health check")
        return jsonify({"status": "unhealthy", "error": "Internal error"}), 503

def handle_get_stats():
    """Handle get statistics request."""
    try:
        if _db_driver is None:
            return jsonify({"error": "Database not initialized"}), 503

        builder = SafeQueryBuilder()

        node_query, node_params = builder.count_nodes()
        node_result = _db_driver.run_safe_query(node_query, node_params)

        rel_query, rel_params = builder.count_relationships()
        rel_result = _db_driver.run_safe_query(rel_query, rel_params)

        if node_result.success and rel_result.success:
            return jsonify(
                {
                    "success": True,
                    "nodes": node_result.data[0]["count"],
                    "relationships": rel_result.data[0]["count"],
                }
            ), 200
        error = node_result.error or rel_result.error
        logger.error("Stats query failed: %s", error)
        return jsonify({"success": False, "error": error}), 500

    except QueryValidationError as e:
        logger.warning("Invalid query in get_stats: %s", e)
        return jsonify({"success": False, "error": "Invalid query"}), 400

    except Neo4jError as e:
        logger.error("Database error in get_stats: %s", e)
        return jsonify({"success": False, "error": "Database error"}), 500

    except Exception as e:
        logger.exception("Unexpected error in get_stats")
        return jsonify({"success": False, "error": "Internal server error"}), 500

def handle_execute_query(request):
    """Handle Cypher query execution."""
    try:
        if _db_driver is None:
            return jsonify({"error": "Database not initialized"}), 503

        data = request.get_json()

        if not data or "query" not in data:
            return jsonify({"error": "Query required"}), 400

        query = data["query"]
        parameters = data.get("parameters", None)

        logger.info("Executing query: %s...", query[:100])

        result = _db_driver.run_safe_query(query, parameters)

        if result.success:
            return jsonify(
                {"success": True, "data": result.data, "count": len(result.data)}
            ), 200
        return jsonify({"success": False, "error": result.error}), 400

    except (BadRequest, UnsupportedMediaType) as e:
        logger.warning("Bad request in execute_query: %s", e)
        return jsonify({"error": "Invalid JSON format"}), 400

    except QueryValidationError as e:
        logger.warning("Invalid query: %s", e)
        return jsonify({"success": False, "error": str(e)}), 400

    except Neo4jError as e:
        logger.error("Database error in execute_query: %s", e)
        return jsonify({"success": False, "error": "Database error"}), 500

    except Exception as e:
        logger.exception("Unexpected error in execute_query")
        return jsonify({"success": False, "error": "Internal server error"}), 500

def handle_autocomplete(request):
    """Handle autocomplete request with optional time filtering.

    Query parameters:
        - q: Search query (minimum 3 characters)
        - label: Optional label filter
        - limit: Maximum results (default: 10, max: 20)
        - start_date: Optional start of time range (ISO format)
        - end_date: Optional end of time range (ISO format)
    """
    try:
        if _autocomplete_service is None:
            return jsonify(
                {"success": False, "error": "Autocomplete service not available"}
            ), 503

        query = request.args.get("q", "").strip()
        label = request.args.get("label", None)
        limit = min(int(request.args.get("limit", 10)), 20)

        start_date = request.args.get("start_date", None)
        end_date = request.args.get("end_date", None)

        if len(query) < 3:
            return jsonify(
                {
                    "success": True,
                    "suggestions": [],
                    "count": 0,
                    "message": "Minimum 3 characters required",
                }
            ), 200

        result = _autocomplete_service.suggest_node_names(
            prefix=query,
            label=label,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
        )

        if result.success and isinstance(result.data, list) and len(result.data) < 3:
            fuzzy_result = _autocomplete_service.fuzzy_search(
                search_term=query,
                label=label,
                limit=limit,
                start_date=start_date,
                end_date=end_date,
            )
            if fuzzy_result.success:
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
        return jsonify({"success": False, "error": result.error}), 500

    except ValueError as e:
        return jsonify({"success": False, "error": f"Invalid parameter: {str(e)}"}), 400

    except QueryValidationError as e:
        logger.warning("Invalid parameters in [HANDLER_NAME]: %s", e)
        return jsonify({"error": str(e)}), 400

    except Neo4jError as e:
        logger.error("Database error in [HANDLER_NAME]: %s", e)
        return jsonify({"error": "Database error"}), 500

    except Exception as e:
        logger.exception("Unexpected error in [HANDLER_NAME]")
        return jsonify({"error": "Internal server error"}), 500

def handle_get_nodes(request):
    """Handle get all nodes request."""
    try:
        if _db_driver is None:
            return jsonify({"error": "Database not initialized"}), 503

        limit = request.args.get("limit", 100, type=int)
        label = request.args.get("label", None)

        builder = SafeQueryBuilder()

        try:
            query, params = builder.get_all_nodes(label=label, limit=limit)
            result = _db_driver.run_safe_query(query, params)

            if result.success:
                return jsonify(
                    {"success": True, "nodes": result.data, "count": len(result.data)}
                ), 200
            logger.error("Get nodes query failed: %s", result.error)
            return jsonify({"success": False, "error": result.error}), 500

        except QueryValidationError as e:
            logger.warning("Validation error: %s", e)
            return jsonify({"error": str(e)}), 400

    except QueryValidationError as e:
        logger.warning("Invalid parameters in [HANDLER_NAME]: %s", e)
        return jsonify({"error": str(e)}), 400

    except Neo4jError as e:
        logger.error("Database error in [HANDLER_NAME]: %s", e)
        return jsonify({"error": "Database error"}), 500

    except Exception as e:
        logger.exception("Unexpected error in [HANDLER_NAME]")
        return jsonify({"error": "Internal server error"}), 500

def handle_create_node(request):
    """Handle create node request.

    IMPORTANT: Should be restricted to authenticated admin users!
    """
    try:
        if _db_driver is None:
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

            result = _db_driver.run_safe_query(query, params)

            if result.success:
                return jsonify(
                    {
                        "success": True,
                        "data": result.data,
        "message": f"Node created with label {label}",
                    }
                ), 201
            return jsonify({"success": False, "error": result.error}), 500

        except QueryValidationError as e:
            logger.warning("Validation error: %s", e)
            return jsonify({"error": str(e)}), 400

    except (BadRequest, UnsupportedMediaType) as e:
        logger.warning("Bad request: %s", e)
        return jsonify({"error": "Invalid JSON format"}), 400

    except QueryValidationError as e:
        logger.warning("Invalid parameters in [HANDLER_NAME]: %s", e)
        return jsonify({"error": str(e)}), 400

    except Neo4jError as e:
        logger.error("Database error in [HANDLER_NAME]: %s", e)
        return jsonify({"error": "Database error"}), 500

    except Exception as e:
        logger.exception("Unexpected error in [HANDLER_NAME]")
        return jsonify({"error": "Internal server error"}), 500

def transform_neo4j_results_to_graph(neo4j_results):
    """Transform Neo4j path results to graph format with full path preservation.

    Args:
        neo4j_results: List of records from Neo4j query, each containing:
            - start: Dict with node properties
            - start_label: String label from Cypher
            - connected: Dict with node properties
            - connected_label: String label from Cypher
            - relationship_details: List of dicts with rel info and node labels

    Returns:
        List with single dict containing:
            - n: Main node data with label
            - connections: List of connection objects
            - nodes: List of all unique nodes with labels
            - edges: List of all edges with source/target
    """
    if not neo4j_results:
        return []

    all_nodes = {}
    all_edges = []
    start_node_key = None

    logger.info("=" * 60)
    logger.info("Starting transformation of %d Neo4j records", len(neo4j_results))
    logger.info("=" * 60)

    for record_idx, record in enumerate(neo4j_results):
        start = record.get("start")
        start_label = record.get("start_label")
        connected = record.get("connected")
        connected_label = record.get("connected_label")
        relationship_details = record.get("relationship_details", [])

        if not start:
            logger.warning("Record %d missing 'start' node", record_idx)
            continue

        start_dict = dict(start)

        if start_label:
            start_dict["label"] = start_label
            logger.debug(
                "Start node: %s with label: %s",
                start_dict.get('name'),
                start_label
            )
        else:
            logger.warning("Start node missing label: %s", start_dict.get('name'))
            start_dict["label"] = "Unknown"

        start_node_key = start_dict.get("name", str(id(start)))

        if start_node_key not in all_nodes:
            all_nodes[start_node_key] = {
                "id": start_node_key,
                "data": start_dict,
                "isMainNode": True,
            }
            logger.debug(
                "Added main node: %s with label: %s",
                start_node_key,
                start_dict['label']
            )

        if connected:
            connected_dict = dict(connected)

            if connected_label:
                connected_dict["label"] = connected_label
            else:
                logger.warning(
                    "Connected node missing label: %s",
                    connected_dict.get('name')
                )
                connected_dict["label"] = "Unknown"

            connected_key = connected_dict.get("name", str(id(connected)))

            if connected_key not in all_nodes:
                all_nodes[connected_key] = {
                    "id": connected_key,
                    "data": connected_dict,
                    "isMainNode": False,
                }
                logger.debug(
                    "Added connected node: %s with label: %s",
                    connected_key,
                    connected_dict['label']
                )

        if relationship_details:
            for rel_detail in relationship_details:
                rel_type = rel_detail.get("type", "CONNECTED")

                source_node_dict = dict(rel_detail.get("start_node", {}))
                source_node_label = rel_detail.get("start_node_label")

                if source_node_label:
                    source_node_dict["label"] = source_node_label
                else:
                    source_node_dict["label"] = "Unknown"

                source_key = source_node_dict.get("name", str(id(source_node_dict)))

                target_node_dict = dict(rel_detail.get("end_node", {}))
                target_node_label = rel_detail.get("end_node_label")

                if target_node_label:
                    target_node_dict["label"] = target_node_label
                else:
                    target_node_dict["label"] = "Unknown"

                target_key = target_node_dict.get("name", str(id(target_node_dict)))

                if source_key not in all_nodes:
                    all_nodes[source_key] = {
                        "id": source_key,
                        "data": source_node_dict,
                        "isMainNode": (source_key == start_node_key),
                    }
                    logger.debug(
                        "Added source node: %s with label: %s",
                        source_key,
                        source_node_dict['label']
                    )

                if target_key not in all_nodes:
                    all_nodes[target_key] = {
                        "id": target_key,
                        "data": target_node_dict,
                        "isMainNode": False,
                    }
                    logger.debug(
                        "Added target node: %s with label: %s",
                        target_key,
                        target_node_dict['label']
                    )

                edge_id = f"{source_key}-{rel_type}-{target_key}"

                if not any(e["id"] == edge_id for e in all_edges):
                    all_edges.append(
                        {
                            "id": edge_id,
                            "source": source_key,
                            "target": target_key,
                            "relationship": rel_type,
                        }
                    )
                    logger.debug(
                        "Added edge: %s -[%s]-> %s",
                        source_key,
                        rel_type,
                        target_key
                    )

    logger.info("=" * 60)
    logger.info("Transformation complete:")
    logger.info("  Total unique nodes: %d", len(all_nodes))
    logger.info("  Total edges: %d", len(all_edges))

    for node_key, node_info in list(all_nodes.items())[:5]:
        has_label = "label" in node_info["data"]
        label_value = node_info["data"].get("label", "MISSING")
        logger.info("  Node '%s': label=%s (present=%s)", node_key, label_value, has_label)

    logger.info("=" * 60)

    if not all_nodes:
        logger.warning("No nodes found after transformation")
        return []

    main_node = None
    for node in all_nodes.values():
        if node.get("isMainNode"):
            main_node = node
            break

    if not main_node:
        main_node = list(all_nodes.values())[0]
        logger.warning("No main node found, using first node: %s", main_node['id'])

    connections = []
    for edge in all_edges:
        target_node = all_nodes.get(edge["target"])
        if target_node:
            connections.append(
                {
                    "relationship": edge["relationship"],
                    "node": target_node["data"],
                    "source": edge["source"],
                    "target": edge["target"],
                }
            )

    result = [
        {
            "n": main_node["data"],
            "connections": connections,
            "nodes": list(all_nodes.values()),
            "edges": all_edges,
        }
    ]

    logger.info(
        "Transformed %d Neo4j records into %d unique nodes with %d edges",
        len(neo4j_results),
        len(all_nodes),
        len(all_edges)
    )

    return result


def handle_get_node_by_name(name, request):
    """Handle get node by name request.

    Uses SafeQueryBuilder for secure, validated query construction.

    Args:
        name: Node name to search for (exact match, case-sensitive)
        request: Flask request object

    Query parameters:
        - label: Node label (required)
        - hops: Context depth 0-3 (default: 1)

    Returns:
        JSON response with node details and relationships
    """
    try:
        if _db_driver is None:
            return jsonify({"error": "Database not initialized"}), 503

        label = request.args.get("label", None)
        hops = int(request.args.get("hops", 1))

        if hops < 0 or hops > 3:
            return jsonify({"error": "Hops must be between 0 and 3"}), 400

        if not label:
            return jsonify({"error": "Label required for node lookup"}), 400

        logger.info("Fetching node: name='%s', label=%s, hops=%s", name, label, hops)

        builder = SafeQueryBuilder()

        try:
            if hops == 0:
                query, params = builder.get_node_with_relationships(
                    property_name="name",
                    property_value=name,
                    label=label,
                    include_metadata=True,
                    limit=1,
                )
            else:
                query, params = builder.find_connected_nodes(
                    start_label=label,
                    start_property="name",
                    start_value=name,
                    max_hops=hops,
                    limit=100,
                )
        except QueryValidationError as e:
            logger.warning("Validation error: %s", e)
            return jsonify({"error": str(e)}), 400

        result = _db_driver.run_safe_query(query, params)

        if result.success:
            if len(result.data) == 0:
                logger.warning("Node not found: '%s' (label=%s)", name, label)
                return jsonify(
                    {"success": False, "error": f"Node '{name}' not found"}
                ), 404

            logger.info("Node found: '%s', returning %d result(s)", name, len(result.data))

            transformed_data = transform_neo4j_results_to_graph(result.data)

            if not transformed_data:
                logger.error("Transformation failed - no data returned")
                return jsonify(
                    {"success": False, "error": "Failed to process node data"}
                ), 500

            return jsonify(
                {
                    "success": True,
                    "data": transformed_data,
                    "count": len(transformed_data[0].get("nodes", [])),
                    "hops": hops,
                }
            ), 200
        logger.error("Get node query failed: %s", result.error)
        return jsonify({"success": False, "error": result.error}), 500

    except ValueError as e:
        logger.warning("Invalid hops parameter: %s", e)
        return jsonify({"error": "Invalid hops parameter - must be integer"}), 400

    except QueryValidationError as e:
        logger.warning("Invalid parameters in [HANDLER_NAME]: %s", e)
        return jsonify({"error": str(e)}), 400

    except Neo4jError as e:
        logger.error("Database error in [HANDLER_NAME]: %s", e)
        return jsonify({"error": "Database error"}), 500

    except Exception as e:
        logger.exception("Unexpected error in [HANDLER_NAME]")
        return jsonify({"error": "Internal server error"}), 500

"""API Routes - URL mapping only.

This module handles route registration and URL mapping.
All business logic lives in handlers.py.
"""

from flask import Blueprint, request
from src.api import handlers

# Create blueprint for API routes
api_bp = Blueprint("api", __name__, url_prefix="/api")


# Health & Status
@api_bp.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return handlers.handle_health_check()


@api_bp.route("/stats", methods=["GET"])
def stats():
    """Get database statistics."""
    return handlers.handle_get_stats()


# Query & Search
@api_bp.route("/query", methods=["POST"])
def query():
    """Execute a Cypher query."""
    return handlers.handle_execute_query(request)


@api_bp.route("/autocomplete", methods=["GET"])
def autocomplete():
    """Get autocomplete suggestions."""
    return handlers.handle_autocomplete(request)


# Nodes
@api_bp.route("/nodes", methods=["GET"])
def get_nodes():
    """Get all nodes (with optional limit)."""
    return handlers.handle_get_nodes(request)


@api_bp.route("/nodes", methods=["POST"])
def create_node():
    """Create a new node."""
    return handlers.handle_create_node(request)


@api_bp.route("/node/<string:name>", methods=["GET"])
def get_node_by_name(name):
    """Get full node details with relationships by name."""
    return handlers.handle_get_node_by_name(name, request)


# more routes later

# @api_bp.route('/relationships', methods=['GET'])
# def get_relationships():
#     """Get relationships between nodes."""
#     return handlers.handle_get_relationships(request)

# @api_bp.route('/search', methods=['GET'])
# def search():
#     """Search nodes by various criteria."""
#     return handlers.handle_search(request)

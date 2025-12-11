"""Data import service for Threat Intelligence data.

This module provides functionality to import ti data from JSON
files into the Neo4j database. It uses the AdminQueryBuilder to create safe,
parameterized Cypher queries and handles validation, transformation, and error
reporting.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from neo4j.exceptions import Neo4jError

from src.driver import GraphDBDriver
from src.logger import setup_logger
from src.services.query_builder import AdminQueryBuilder, QueryValidationError


@dataclass
class ImportResult:
    """Result of a data import operation.

    Attributes:
        success: Whether the import completed successfully.
        nodes_created: Number of nodes created/merged.
        relationships_created: Number of relationships created/merged.
        errors: List of error messages (if any).
        warnings: List of warning messages (if any).
        duration_seconds: Time taken for import.
        metadata: Metadata from the JSON file.
    """

    success: bool
    nodes_created: int = 0
    relationships_created: int = 0
    errors: List[str] = None
    warnings: List[str] = None
    duration_seconds: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "nodes_created": self.nodes_created,
            "relationships_created": self.relationships_created,
            "errors": self.errors,
            "warnings": self.warnings,
            "duration_seconds": round(self.duration_seconds, 2),
            "metadata": self.metadata,
        }


class ImportService:
    """Service for importing threat intelligence data from JSON files.

    This service handles:
    - Loading and validating JSON files
    - Transforming data for AdminQueryBuilder
    - Batch importing nodes and relationships
    - Error handling and reporting
    - Transaction management
    """

    def __init__(self, driver: GraphDBDriver, log_level: int = logging.INFO):
        """Initialize the import service.

        Args:
            driver: Neo4j database driver.
            log_level: Logging level (default: INFO).
        """
        self.driver = driver
        self.builder = AdminQueryBuilder()
        self.logger = setup_logger("ImportService", log_level)

    def load_json_file(self, filepath: str) -> Dict[str, Any]:
        """Load and parse JSON file.

        Args:
            filepath: Path to JSON file.

        Returns:
            Parsed JSON data.

        Raises:
            FileNotFoundError: If file doesn't exist.
            json.JSONDecodeError: If file is not valid JSON.
        """
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        self.logger.info("Loading JSON file: %s", filepath)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.logger.info("Loaded JSON file (%d bytes)", path.stat().st_size)
        return data

    def validate_json_structure(self, data: Dict[str, Any]) -> List[str]:
        """Validate basic JSON structure.

        Args:
            data: Parsed JSON data.

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        # Check required top-level keys
        if "nodes" not in data:
            errors.append("Missing 'nodes' key in JSON")
        elif not isinstance(data["nodes"], list):
            errors.append("'nodes' must be a list")

        if "relationships" not in data:
            errors.append("Missing 'relationships' key in JSON")
        elif not isinstance(data["relationships"], list):
            errors.append("'relationships' must be a list")

        # Check metadata (optional but recommended)
        if "metadata" in data:
            metadata = data["metadata"]
            if not isinstance(metadata, dict):
                errors.append("'metadata' must be an object")
            elif "version" not in metadata:
                errors.append("'metadata' is missing 'version' field")

        return errors

    def validate_nodes(
        self, nodes: List[Dict[str, Any]]
    ) -> tuple[List[str], List[str]]:
        """Validate node data against whitelists.

        Args:
            nodes: List of node objects.

        Returns:
            Tuple of (errors, warnings).
        """
        errors = []
        warnings = []

        for idx, node in enumerate(nodes):
            # Check required fields
            if "label" not in node:
                errors.append(f"Node {idx}: Missing 'label' field")
                continue

            if "properties" not in node:
                errors.append(f"Node {idx}: Missing 'properties' field")
                continue

            # Validate label
            try:
                self.builder.validate_label(node["label"])
            except QueryValidationError as e:
                errors.append(f"Node {idx}: {str(e)}")

            # Validate properties
            properties = node["properties"]
            if not isinstance(properties, dict):
                errors.append(f"Node {idx}: 'properties' must be an object")
                continue

            # Check for 'name' property (most nodes need it)
            if "name" not in properties and node["label"] != "Identity":
                warnings.append(
                    f"Node {idx} ({node['label']}): Missing 'name' property, "
                    "may cause import issues"
                )

            # Validate each property name
            for prop_name in properties.keys():
                try:
                    self.builder.validate_property(prop_name)
                except QueryValidationError as e:
                    errors.append(f"Node {idx}: {str(e)}")

        return errors, warnings

    def validate_relationships(
        self,
        relationships: List[Dict[str, Any]],
        existing_nodes: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[List[str], List[str]]:
        """Validate relationship data.

        Args:
            relationships: List of relationship objects.
            existing_nodes: Optional list of nodes to check references.

        Returns:
            Tuple of (errors, warnings).
        """
        errors = []
        warnings = []

        # Build node index if provided
        node_index = {}
        if existing_nodes:
            for node in existing_nodes:
                label = node.get("label")
                props = node.get("properties", {})
                # Index by label and name
                if "name" in props:
                    key = f"{label}:{props['name']}"
                    node_index[key] = node

        for idx, rel in enumerate(relationships):
            # Check required fields
            required_fields = ["type", "from", "to"]
            for field in required_fields:
                if field not in rel:
                    errors.append(f"Relationship {idx}: Missing '{field}' field")

            if len(errors) > idx:  # Skip further validation if missing required fields
                continue

            # Validate relationship type
            try:
                self.builder.validate_relationship(rel["type"])
            except QueryValidationError as e:
                errors.append(f"Relationship {idx}: {str(e)}")

            # Validate 'from' and 'to' structure
            for direction in ["from", "to"]:
                node_ref = rel[direction]
                if not isinstance(node_ref, dict):
                    errors.append(
                        f"Relationship {idx}: '{direction}' must be an object"
                    )
                    continue

                # Check required fields in node reference
                for field in ["label", "property", "value"]:
                    if field not in node_ref:
                        errors.append(
                            f"Relationship {idx}: '{direction}.{field}' is required"
                        )

                # Validate label
                if "label" in node_ref:
                    try:
                        self.builder.validate_label(node_ref["label"])
                    except QueryValidationError as e:
                        errors.append(f"Relationship {idx}: {direction} - {str(e)}")

                # Validate property name
                if "property" in node_ref:
                    try:
                        self.builder.validate_property(node_ref["property"])
                    except QueryValidationError as e:
                        errors.append(f"Relationship {idx}: {direction} - {str(e)}")

                # Check if referenced node exists (if we have the index)
                if node_index and "label" in node_ref and "value" in node_ref:
                    # Currently only checks 'name' property
                    if node_ref.get("property") == "name":
                        key = f"{node_ref['label']}:{node_ref['value']}"
                        if key not in node_index:
                            warnings.append(
                                f"Relationship {idx}: Referenced node not found: "
                                f"{node_ref['label']} with name='{node_ref['value']}'"
                            )

            # Validate relationship properties if present
            if "properties" in rel and rel["properties"]:
                for prop_name in rel["properties"].keys():
                    try:
                        self.builder.validate_property(prop_name)
                    except QueryValidationError as e:
                        errors.append(f"Relationship {idx}: {str(e)}")

        return errors, warnings

    def transform_relationships(
        self, relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Transform relationship format for AdminQueryBuilder.

        Transforms from JSON format:
        {
          "type": "USES",
          "from": {"label": "X", "property": "name", "value": "Y"},
          "to": {"label": "A", "property": "name", "value": "B"},
          "properties": {...}
        }

        To AdminQueryBuilder format:
        {
          "from_label": "X",
          "from_value": "Y",
          "to_label": "A",
          "to_value": "B",
          "type": "USES",
          "properties": {...}
        }

        Args:
            relationships: List of relationships in JSON format.

        Returns:
            List of relationships in AdminQueryBuilder format.
        """
        transformed = []

        for rel in relationships:
            # Note: Currently assumes 'name' property for matching
            # In future, could support custom match_property per relationship
            transformed_rel = {
                "from_label": rel["from"]["label"],
                "from_value": rel["from"]["value"],
                "to_label": rel["to"]["label"],
                "to_value": rel["to"]["value"],
                "type": rel["type"],
            }

            # Add properties if present
            if "properties" in rel and rel["properties"]:
                transformed_rel["properties"] = rel["properties"]

            transformed.append(transformed_rel)

        return transformed

    def import_nodes(self, nodes: List[Dict[str, Any]]) -> int:
        """Import nodes into database using batch merge.

        Args:
            nodes: List of node objects.

        Returns:
            Total number of nodes processed across all labels.

        Raises:
            RuntimeError: If import fails.
        """
        if not nodes:
            self.logger.info("No nodes to import")
            return 0

        self.logger.info("Importing %d nodes...", len(nodes))

        # Get list of queries (one per label)
        queries = self.builder.merge_nodes_batch(nodes)

        total_count = 0
        label_counts = {}

        # Execute each query separately
        for query, params in queries:
            result = self.driver.execute(query, params, write=True)

            # Extract count and label from result
            if result and len(result) > 0:
                count = result[0].get("count", 0)
                label = result[0].get("label", "Unknown")
                label_counts[label] = count
                total_count += count
                self.logger.info(" %s: %d nodes", label, count)

        self.logger.info(
            "Imported %d nodes total across %d labels",
            total_count,
            len(label_counts)
        )

        return total_count

    def import_relationships(self, relationships: List[Dict[str, Any]]) -> int:
        """Import relationships into database using batch merge.

        Args:
            relationships: List of relationship objects (in AdminQueryBuilder format).

        Returns:
            Total number of relationships processed across all patterns.

        Raises:
            RuntimeError: If import fails.
        """
        if not relationships:
            self.logger.info("No relationships to import")
            return 0

        self.logger.info("Importing %d relationships...", len(relationships))

        # Get list of queries (one per relationship pattern)
        queries = self.builder.merge_relationships_batch(relationships)

        total_count = 0
        pattern_counts = []

        # Execute each query separately
        for query, params in queries:
            result = self.driver.execute(query, params, write=True)

            # Extract count and pattern info from result
            if result and len(result) > 0:
                count = result[0].get("count", 0)
                from_label = result[0].get("from_label", "?")
                to_label = result[0].get("to_label", "?")
                rel_type = result[0].get("type", "?")
                pattern_counts.append((from_label, rel_type, to_label, count))
                total_count += count
                self.logger.info(
                    " (%s)-[%s]->(%s): %d relationships",
                    from_label,
                    rel_type,
                    to_label,
                    count
                )

        self.logger.info(
            "Imported %d relationships total across %d patterns",
            total_count,
            len(pattern_counts)
        )

        return total_count

    def import_from_json(
        self, filepath: str, validate: bool = True, dry_run: bool = False
    ) -> ImportResult:
        """Import data from JSON file into Neo4j database.

        This is the main entry point for importing data. It:
        1. Loads the JSON file
        2. Validates structure and data
        3. Imports nodes (batch)
        4. Imports relationships (batch)
        5. Returns detailed results

        Args:
            filepath: Path to JSON file.
            validate: Whether to validate data before import (default: True).
            dry_run: If True, validate but don't import (default: False).

        Returns:
            ImportResult with statistics and any errors/warnings.
        """
        start_time = datetime.now()
        result = ImportResult(success=False)

        try:
            # Load JSON file
            data = self.load_json_file(filepath)
            result.metadata = data.get("metadata")

            # Validate JSON structure
            if validate:
                self.logger.info("Validating JSON structure...")
                structure_errors = self.validate_json_structure(data)
                if structure_errors:
                    result.errors.extend(structure_errors)
                    self.logger.error("X JSON structure validation failed")
                    for error in structure_errors:
                        self.logger.error("  - %s", error)
                    return result
                self.logger.info("JSON structure is valid")

            nodes = data.get("nodes", [])
            relationships = data.get("relationships", [])

            # Validate nodes
            if validate:
                self.logger.info("Validating %d nodes...", len(nodes))
                node_errors, node_warnings = self.validate_nodes(nodes)
                result.errors.extend(node_errors)
                result.warnings.extend(node_warnings)

                if node_errors:
                    self.logger.error(
                        "Node validation failed with %d errors",
                        len(node_errors)
                    )
                    for error in node_errors[:5]:  # Show first 5
                        self.logger.error("  - %s", error)
                    if len(node_errors) > 5:
                        self.logger.error(
                            "  ... and %d more errors",
                            len(node_errors) - 5
                        )
                    return result

                if node_warnings:
                    self.logger.warning(" %d warnings", len(node_warnings))
                    for warning in node_warnings[:3]:  # Show first 3
                        self.logger.warning("  - %s", warning)

                self.logger.info(" Node validation passed")

            # Validate relationships
            if validate:
                self.logger.info("Validating %d relationships...", len(relationships))
                rel_errors, rel_warnings = self.validate_relationships(
                    relationships, existing_nodes=nodes
                )
                result.errors.extend(rel_errors)
                result.warnings.extend(rel_warnings)

                if rel_errors:
                    self.logger.error(
                        " Relationship validation failed with %d errors",
                        len(rel_errors)
                    )
                    for error in rel_errors[:5]:
                        self.logger.error("  - %s", error)
                    if len(rel_errors) > 5:
                        self.logger.error(
                            "  ... and %d more errors",
                            len(rel_errors) - 5
                        )
                    return result

                if rel_warnings:
                    self.logger.warning(" %d warnings", len(rel_warnings))
                    for warning in rel_warnings[:3]:
                        self.logger.warning("  - %s", warning)

                self.logger.info(" Relationship validation passed")

            # Dry run - stop here
            if dry_run:
                self.logger.info(" Dry run completed - no data imported")
                result.success = True
                return result

            # Import nodes
            self.logger.info("=" * 60)
            self.logger.info("Starting import...")
            self.logger.info("=" * 60)

            try:
                result.nodes_created = self.import_nodes(nodes)
            except QueryValidationError as e:
                error_msg = f"Invalid query during node import: {str(e)}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)
                return result
            except Neo4jError as e:
                error_msg = f"Database error during node import: {str(e)}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)
                return result
            except Exception as e:
                error_msg = f"Failed to import nodes: {str(e)}"
                self.logger.exception("Unexpected error in node import")
                result.errors.append(error_msg)
                return result

            # Transform and import relationships
            try:
                transformed_rels = self.transform_relationships(relationships)
                result.relationships_created = self.import_relationships(transformed_rels)
            except QueryValidationError as e:
                error_msg = f"Invalid query during relationship import: {str(e)}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)
            except Neo4jError as e:
                error_msg = f"Database error during relationship import: {str(e)}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)
            except Exception as e:
                error_msg = f"Failed to import relationships: {str(e)}"
                self.logger.exception("Unexpected error in relationship import")
                result.errors.append(error_msg)

            # Success!
            result.success = True

            self.logger.info("=" * 60)
            self.logger.info(" Import completed successfully!")
            self.logger.info("  Nodes: %d", result.nodes_created)
            self.logger.info("  Relationships: %d", result.relationships_created)
            if result.warnings:
                self.logger.info("  Warnings: %d", len(result.warnings))
            self.logger.info("=" * 60)

        except FileNotFoundError as e:
            error_msg = str(e)
            self.logger.error(" %s", error_msg)
            result.errors.append(error_msg)

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON: {str(e)}"
            self.logger.error(" %s", error_msg)
            result.errors.append(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.exception("Full traceback of unexpected error")
            result.errors.append(error_msg)

        finally:
            # Calculate duration
            end_time = datetime.now()
            result.duration_seconds = (end_time - start_time).total_seconds()

        return result

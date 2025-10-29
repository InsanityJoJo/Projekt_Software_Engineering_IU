"""Unit tests for the ImportService class.

This module tests the import service's ability to load, validate,
and import threat intelligence data from JSON files into Neo4j.
All fixtures are defined in conftest.py for reusability.
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from src.services.import_service import ImportService, ImportResult
from src.services.query_builder import QueryValidationError


class TestLoadJsonFile:
    """Test suite for load_json_file method."""

    def test_load_valid_json_file(self, import_service, temp_json_file):
        """Test loading a valid JSON file."""
        data = import_service.load_json_file(temp_json_file)

        assert "metadata" in data
        assert "nodes" in data
        assert "relationships" in data
        assert data["metadata"]["version"] == "1.0"

    def test_load_nonexistent_file(self, import_service):
        """Test that loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError) as exc_info:
            import_service.load_json_file("/nonexistent/file.json")

        assert "File not found" in str(exc_info.value)

    def test_load_invalid_json(self, import_service, invalid_json_file):
        """Test that loading invalid JSON raises JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError):
            import_service.load_json_file(invalid_json_file)


class TestValidateJsonStructure:
    """Test suite for validate_json_structure method."""

    def test_validate_complete_structure(self, import_service, valid_json_data):
        """Test validation of complete, valid JSON structure."""
        errors = import_service.validate_json_structure(valid_json_data)

        assert errors == []

    def test_validate_missing_nodes(self, import_service):
        """Test validation fails when 'nodes' key is missing."""
        data = {
            "relationships": [],
            "metadata": {"version": "1.0"},
        }

        errors = import_service.validate_json_structure(data)

        assert len(errors) > 0
        assert any("nodes" in error.lower() for error in errors)

    def test_validate_missing_relationships(self, import_service):
        """Test validation fails when 'relationships' key is missing."""
        data = {
            "nodes": [],
            "metadata": {"version": "1.0"},
        }

        errors = import_service.validate_json_structure(data)

        assert len(errors) > 0
        assert any("relationships" in error.lower() for error in errors)

    def test_validate_nodes_not_list(self, import_service):
        """Test validation fails when 'nodes' is not a list."""
        data = {
            "nodes": "not a list",
            "relationships": [],
        }

        errors = import_service.validate_json_structure(data)

        assert len(errors) > 0
        assert any("must be a list" in error for error in errors)

    def test_validate_relationships_not_list(self, import_service):
        """Test validation fails when 'relationships' is not a list."""
        data = {
            "nodes": [],
            "relationships": "not a list",
        }

        errors = import_service.validate_json_structure(data)

        assert len(errors) > 0
        assert any("must be a list" in error for error in errors)

    def test_validate_metadata_not_dict(self, import_service):
        """Test validation fails when 'metadata' is not a dict."""
        data = {
            "nodes": [],
            "relationships": [],
            "metadata": "not a dict",
        }

        errors = import_service.validate_json_structure(data)

        assert len(errors) > 0
        assert any("metadata" in error.lower() for error in errors)

    def test_validate_missing_version_in_metadata(self, import_service):
        """Test validation fails when metadata lacks 'version'."""
        data = {
            "nodes": [],
            "relationships": [],
            "metadata": {"source": "Test"},  # Missing 'version'
        }

        errors = import_service.validate_json_structure(data)

        assert len(errors) > 0
        assert any("version" in error.lower() for error in errors)


class TestValidateNodes:
    """Test suite for validate_nodes method."""

    def test_validate_valid_nodes(self, import_service, sample_nodes):
        """Test validation of valid nodes."""
        errors, warnings = import_service.validate_nodes(sample_nodes)

        assert errors == []
        assert warnings == []

    def test_validate_node_missing_label(self, import_service):
        """Test validation fails for node without label."""
        nodes = [
            {"properties": {"name": "Test"}},
        ]

        errors, warnings = import_service.validate_nodes(nodes)

        assert len(errors) > 0
        assert any("label" in error.lower() for error in errors)

    def test_validate_node_missing_properties(self, import_service):
        """Test validation fails for node without properties."""
        nodes = [
            {"label": "ThreatActor"},
        ]

        errors, warnings = import_service.validate_nodes(nodes)

        assert len(errors) > 0
        assert any("properties" in error.lower() for error in errors)

    def test_validate_node_invalid_label(self, import_service):
        """Test validation fails for invalid label."""
        nodes = [
            {"label": "InvalidLabel", "properties": {"name": "Test"}},
        ]

        errors, warnings = import_service.validate_nodes(nodes)

        assert len(errors) > 0
        assert any("not allowed" in error for error in errors)

    def test_validate_node_invalid_property(self, import_service):
        """Test validation fails for invalid property."""
        nodes = [
            {
                "label": "ThreatActor",
                "properties": {"name": "APT28", "invalid_prop": "value"},
            },
        ]

        errors, warnings = import_service.validate_nodes(nodes)

        assert len(errors) > 0
        assert any("not allowed" in error for error in errors)

    def test_validate_node_missing_name_property_warning(self, import_service):
        """Test warning for node missing 'name' property."""
        nodes = [
            {
                "label": "ThreatActor",
                "properties": {"type": "Nation-State"},  # Missing 'name'
            },
        ]

        errors, warnings = import_service.validate_nodes(nodes)

        assert len(warnings) > 0
        assert any("name" in warning.lower() for warning in warnings)

    def test_validate_node_properties_not_dict(self, import_service):
        """Test validation fails when properties is not a dict."""
        nodes = [
            {"label": "ThreatActor", "properties": "not a dict"},
        ]

        errors, warnings = import_service.validate_nodes(nodes)

        assert len(errors) > 0
        assert any("must be an object" in error for error in errors)


class TestValidateRelationships:
    """Test suite for validate_relationships method."""

    def test_validate_valid_relationships(
        self, import_service, sample_nodes, sample_relationships
    ):
        """Test validation of valid relationships."""
        errors, warnings = import_service.validate_relationships(
            sample_relationships, sample_nodes
        )

        assert errors == []

    def test_validate_relationship_missing_type(self, import_service):
        """Test validation fails for relationship without type."""
        relationships = [
            {
                "from": {"label": "ThreatActor", "property": "name", "value": "APT28"},
                "to": {"label": "Malware", "property": "name", "value": "X-Agent"},
            },
        ]

        errors, warnings = import_service.validate_relationships(relationships)

        assert len(errors) > 0
        assert any("type" in error.lower() for error in errors)

    def test_validate_relationship_missing_from(self, import_service):
        """Test validation fails for relationship without 'from'."""
        relationships = [
            {
                "type": "USES",
                "to": {"label": "Malware", "property": "name", "value": "X-Agent"},
            },
        ]

        errors, warnings = import_service.validate_relationships(relationships)

        assert len(errors) > 0
        assert any("from" in error.lower() for error in errors)

    def test_validate_relationship_missing_to(self, import_service):
        """Test validation fails for relationship without 'to'."""
        relationships = [
            {
                "type": "USES",
                "from": {"label": "ThreatActor", "property": "name", "value": "APT28"},
            },
        ]

        errors, warnings = import_service.validate_relationships(relationships)

        assert len(errors) > 0
        assert any("to" in error.lower() for error in errors)

    def test_validate_relationship_invalid_type(self, import_service):
        """Test validation fails for invalid relationship type."""
        relationships = [
            {
                "type": "INVALID_REL",
                "from": {"label": "ThreatActor", "property": "name", "value": "APT28"},
                "to": {"label": "Malware", "property": "name", "value": "X-Agent"},
            },
        ]

        errors, warnings = import_service.validate_relationships(relationships)

        assert len(errors) > 0
        assert any("not allowed" in error for error in errors)

    def test_validate_relationship_invalid_from_label(self, import_service):
        """Test validation fails for invalid 'from' label."""
        relationships = [
            {
                "type": "USES",
                "from": {"label": "InvalidLabel", "property": "name", "value": "Test"},
                "to": {"label": "Malware", "property": "name", "value": "X-Agent"},
            },
        ]

        errors, warnings = import_service.validate_relationships(relationships)

        assert len(errors) > 0
        assert any("not allowed" in error for error in errors)

    def test_validate_relationship_invalid_to_label(self, import_service):
        """Test validation fails for invalid 'to' label."""
        relationships = [
            {
                "type": "USES",
                "from": {"label": "ThreatActor", "property": "name", "value": "APT28"},
                "to": {"label": "InvalidLabel", "property": "name", "value": "Test"},
            },
        ]

        errors, warnings = import_service.validate_relationships(relationships)

        assert len(errors) > 0
        assert any("not allowed" in error for error in errors)


class TestTransformRelationships:
    """Test suite for transform_relationships method."""

    def test_transform_basic_relationships(self, import_service):
        """Test basic relationship transformation."""
        relationships = [
            {
                "type": "USES",
                "from": {"label": "ThreatActor", "value": "APT28"},
                "to": {"label": "Malware", "value": "X-Agent"},
            },
        ]

        transformed = import_service.transform_relationships(relationships)

        assert len(transformed) == 1
        assert transformed[0]["from_label"] == "ThreatActor"
        assert transformed[0]["from_value"] == "APT28"
        assert transformed[0]["to_label"] == "Malware"
        assert transformed[0]["to_value"] == "X-Agent"
        assert transformed[0]["type"] == "USES"

    def test_transform_relationships_with_properties(self, import_service):
        """Test transformation preserves relationship properties."""
        relationships = [
            {
                "type": "USES",
                "from": {"label": "ThreatActor", "value": "APT28"},
                "to": {"label": "Malware", "value": "X-Agent"},
                "properties": {"source": "Report 1", "first_seen": "2020-01-01"},
            },
        ]

        transformed = import_service.transform_relationships(relationships)

        assert len(transformed) == 1
        assert "properties" in transformed[0]
        assert transformed[0]["properties"]["source"] == "Report 1"
        assert transformed[0]["properties"]["first_seen"] == "2020-01-01"

    def test_transform_relationships_without_properties(self, import_service):
        """Test transformation handles missing properties."""
        relationships = [
            {
                "type": "USES",
                "from": {"label": "ThreatActor", "value": "APT28"},
                "to": {"label": "Malware", "value": "X-Agent"},
            },
        ]

        transformed = import_service.transform_relationships(relationships)

        assert len(transformed) == 1
        # Should not have 'properties' key if not present in original
        assert (
            "properties" not in transformed[0] or transformed[0]["properties"] is None
        )


class TestImportNodes:
    """Test suite for import_nodes method."""

    def test_import_nodes_success(
        self, import_service, mock_import_driver, sample_nodes
    ):
        """Test successful node import."""
        # Mock the execute method to return proper results
        mock_import_driver.execute.side_effect = [
            [{"count": 1, "label": "ThreatActor"}],
            [{"count": 1, "label": "Malware"}],
        ]

        count = import_service.import_nodes(sample_nodes)

        assert count == 2
        # Verify execute was called twice (once per label)
        assert mock_import_driver.execute.call_count == 2

    def test_import_nodes_empty_list(self, import_service, mock_import_driver):
        """Test importing empty node list."""
        nodes = []

        count = import_service.import_nodes(nodes)

        assert count == 0
        # Should not call execute for empty list
        assert mock_import_driver.execute.call_count == 0

    def test_import_nodes_tracks_per_label_counts(
        self, import_service, mock_import_driver
    ):
        """Test that import tracks counts per label."""
        nodes = [
            {"label": "ThreatActor", "properties": {"name": "APT28"}},
            {"label": "ThreatActor", "properties": {"name": "APT29"}},
            {"label": "Malware", "properties": {"name": "X-Agent"}},
        ]

        # Mock returns for two queries
        mock_import_driver.execute.side_effect = [
            [{"count": 2, "label": "ThreatActor"}],  # 2 ThreatActors
            [{"count": 1, "label": "Malware"}],  # 1 Malware
        ]

        count = import_service.import_nodes(nodes)

        assert count == 3

    def test_import_nodes_handles_errors(self, import_service, mock_import_driver):
        """Test that import handles database errors."""
        nodes = [
            {"label": "ThreatActor", "properties": {"name": "APT28"}},
        ]

        # Mock execute to raise an exception
        mock_import_driver.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            import_service.import_nodes(nodes)

        assert "Database error" in str(exc_info.value)


class TestImportRelationships:
    """Test suite for import_relationships method."""

    def test_import_relationships_success(self, import_service, mock_import_driver):
        """Test successful relationship import."""
        relationships = [
            {
                "from_label": "ThreatActor",
                "from_value": "APT28",
                "to_label": "Malware",
                "to_value": "X-Agent",
                "type": "USES",
            },
        ]

        # Mock the execute method
        mock_import_driver.execute.return_value = [
            {
                "count": 1,
                "from_label": "ThreatActor",
                "to_label": "Malware",
                "type": "USES",
            }
        ]

        count = import_service.import_relationships(relationships)

        assert count == 1
        assert mock_import_driver.execute.call_count == 1

    def test_import_relationships_empty_list(self, import_service, mock_import_driver):
        """Test importing empty relationship list."""
        relationships = []

        count = import_service.import_relationships(relationships)

        assert count == 0
        assert mock_import_driver.execute.call_count == 0

    def test_import_relationships_multiple_patterns(
        self, import_service, mock_import_driver
    ):
        """Test importing relationships with multiple patterns."""
        relationships = [
            {
                "from_label": "ThreatActor",
                "from_value": "APT28",
                "to_label": "Malware",
                "to_value": "X-Agent",
                "type": "USES",
            },
            {
                "from_label": "Campaign",
                "from_value": "Op X",
                "to_label": "ThreatActor",
                "to_value": "APT28",
                "type": "LAUNCHED",
            },
        ]

        # Mock returns for two different patterns
        mock_import_driver.execute.side_effect = [
            [
                {
                    "count": 1,
                    "from_label": "ThreatActor",
                    "to_label": "Malware",
                    "type": "USES",
                }
            ],
            [
                {
                    "count": 1,
                    "from_label": "Campaign",
                    "to_label": "ThreatActor",
                    "type": "LAUNCHED",
                }
            ],
        ]

        count = import_service.import_relationships(relationships)

        assert count == 2
        assert mock_import_driver.execute.call_count == 2


class TestImportFromJson:
    """Test suite for import_from_json method (main entry point)."""

    def test_import_from_json_success(
        self, import_service, mock_import_driver, temp_json_file
    ):
        """Test successful complete import from JSON file."""
        # Mock execute to return proper results
        mock_import_driver.execute.side_effect = [
            [{"count": 1, "label": "ThreatActor"}],
            [{"count": 1, "label": "Malware"}],
            [
                {
                    "count": 1,
                    "from_label": "ThreatActor",
                    "to_label": "Malware",
                    "type": "USES",
                }
            ],
        ]

        result = import_service.import_from_json(temp_json_file)

        assert result.success is True
        assert result.nodes_created == 2
        assert result.relationships_created == 1
        assert result.errors == []
        assert result.metadata is not None
        assert result.duration_seconds >= 0

    def test_import_from_json_with_validation(
        self, import_service, mock_import_driver, temp_json_file
    ):
        """Test import with validation enabled."""
        mock_import_driver.execute.side_effect = [
            [{"count": 1, "label": "ThreatActor"}],
            [{"count": 1, "label": "Malware"}],
            [
                {
                    "count": 1,
                    "from_label": "ThreatActor",
                    "to_label": "Malware",
                    "type": "USES",
                }
            ],
        ]

        result = import_service.import_from_json(temp_json_file, validate=True)

        assert result.success is True
        assert len(result.errors) == 0

    def test_import_from_json_without_validation(
        self, import_service, mock_import_driver, temp_json_file
    ):
        """Test import with validation disabled."""
        mock_import_driver.execute.side_effect = [
            [{"count": 1, "label": "ThreatActor"}],
            [{"count": 1, "label": "Malware"}],
            [
                {
                    "count": 1,
                    "from_label": "ThreatActor",
                    "to_label": "Malware",
                    "type": "USES",
                }
            ],
        ]

        result = import_service.import_from_json(temp_json_file, validate=False)

        assert result.success is True

    def test_import_from_json_dry_run(
        self, import_service, mock_import_driver, temp_json_file
    ):
        """Test dry run mode (validation only, no import)."""
        result = import_service.import_from_json(temp_json_file, dry_run=True)

        assert result.success is True
        assert result.nodes_created == 0
        assert result.relationships_created == 0
        # Should not call execute in dry run mode
        assert mock_import_driver.execute.call_count == 0

    def test_import_from_json_file_not_found(self, import_service):
        """Test handling of nonexistent file."""
        result = import_service.import_from_json("/nonexistent/file.json")

        assert result.success is False
        assert len(result.errors) > 0
        assert any("File not found" in error for error in result.errors)

    def test_import_from_json_invalid_structure(self, import_service):
        """Test handling of invalid JSON structure."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {"invalid": "structure"}, f
            )  # Missing 'nodes' and 'relationships'
            temp_path = f.name

        try:
            result = import_service.import_from_json(temp_path)

            assert result.success is False
            assert len(result.errors) > 0
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_import_from_json_validation_errors(self, import_service):
        """Test handling of validation errors in data."""
        data = {
            "metadata": {"version": "1.0"},
            "nodes": [
                {
                    "label": "InvalidLabel",
                    "properties": {"name": "Test"},
                },  # Invalid label
            ],
            "relationships": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            result = import_service.import_from_json(temp_path, validate=True)

            assert result.success is False
            assert len(result.errors) > 0
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_import_from_json_database_error_nodes(
        self, import_service, mock_import_driver, temp_json_file
    ):
        """Test handling of database errors during node import."""
        mock_import_driver.execute.side_effect = Exception("Database connection failed")

        result = import_service.import_from_json(temp_json_file, validate=False)

        assert result.success is False
        assert len(result.errors) > 0
        assert any("Failed to import nodes" in error for error in result.errors)

    def test_import_from_json_database_error_relationships(
        self, import_service, mock_import_driver, temp_json_file
    ):
        """Test handling of database errors during relationship import."""
        # Nodes succeed, relationships fail
        mock_import_driver.execute.side_effect = [
            [{"count": 1, "label": "ThreatActor"}],
            [{"count": 1, "label": "Malware"}],
            Exception("Database error during relationships"),
        ]

        result = import_service.import_from_json(temp_json_file, validate=False)

        # Should still report success for nodes, but have error for relationships
        assert result.nodes_created == 2
        assert result.relationships_created == 0
        assert len(result.errors) > 0
        assert any("Failed to import relationships" in error for error in result.errors)

    def test_import_from_json_tracks_duration(
        self, import_service, mock_import_driver, temp_json_file
    ):
        """Test that import tracks execution duration."""
        mock_import_driver.execute.side_effect = [
            [{"count": 1, "label": "ThreatActor"}],
            [{"count": 1, "label": "Malware"}],
            [
                {
                    "count": 1,
                    "from_label": "ThreatActor",
                    "to_label": "Malware",
                    "type": "USES",
                }
            ],
        ]

        result = import_service.import_from_json(temp_json_file)

        assert result.duration_seconds >= 0
        assert isinstance(result.duration_seconds, float)

    def test_import_from_json_preserves_metadata(
        self, import_service, mock_import_driver, temp_json_file
    ):
        """Test that metadata from JSON is preserved in result."""
        mock_import_driver.execute.side_effect = [
            [{"count": 1, "label": "ThreatActor"}],
            [{"count": 1, "label": "Malware"}],
            [
                {
                    "count": 1,
                    "from_label": "ThreatActor",
                    "to_label": "Malware",
                    "type": "USES",
                }
            ],
        ]

        result = import_service.import_from_json(temp_json_file)

        assert result.metadata is not None
        assert result.metadata["version"] == "1.0"
        assert result.metadata["source"] == "Test Source"


class TestImportResult:
    """Test suite for ImportResult dataclass."""

    def test_import_result_defaults(self):
        """Test ImportResult default values."""
        result = ImportResult(success=True)

        assert result.success is True
        assert result.nodes_created == 0
        assert result.relationships_created == 0
        assert result.errors == []
        assert result.warnings == []
        assert result.duration_seconds == 0.0
        assert result.metadata is None

    def test_import_result_to_dict(self):
        """Test ImportResult conversion to dictionary."""
        result = ImportResult(
            success=True,
            nodes_created=10,
            relationships_created=15,
            errors=["error1"],
            warnings=["warning1"],
            duration_seconds=1.234,
            metadata={"version": "1.0"},
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["nodes_created"] == 10
        assert result_dict["relationships_created"] == 15
        assert result_dict["errors"] == ["error1"]
        assert result_dict["warnings"] == ["warning1"]
        assert result_dict["duration_seconds"] == 1.23  # Rounded to 2 decimals
        assert result_dict["metadata"]["version"] == "1.0"

    def test_import_result_post_init(self):
        """Test that post_init initializes empty lists."""
        result = ImportResult(success=True, errors=None, warnings=None)

        assert result.errors == []
        assert result.warnings == []

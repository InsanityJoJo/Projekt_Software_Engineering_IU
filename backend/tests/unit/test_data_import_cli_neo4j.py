"""Integration tests for data import over service layer in backend into Neo4j.

This module tests AdminQueryBuilder and ImportService's ability to create
write operations with successful storage of data in Neo4j.
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from src.services.query_builder import AdminQueryBuilder
from src.services.import_service import ImportService


class TestAdminQueryBuilderIntegration:
    """Integration tests for AdminQueryBuilder with realistic scenarios."""

    def test_import_scenario(self):
        """Test a realistic import scenario with mixed nodes and relationships."""
        builder = AdminQueryBuilder()

        # Typical import: multiple node types
        nodes = [
            {
                "label": "ThreatActor",
                "properties": {"name": "APT28", "type": "Nation-State"},
            },
            {
                "label": "ThreatActor",
                "properties": {"name": "APT29", "type": "Nation-State"},
            },
            {"label": "Malware", "properties": {"name": "X-Agent", "family": "Sofacy"}},
            {
                "label": "Campaign",
                "properties": {"name": "Operation Aurora", "start_date": "2020-01-01"},
            },
            {"label": "Tool", "properties": {"name": "Mimikatz", "version": "2.2.0"}},
        ]

        # Get queries
        node_queries = builder.merge_nodes_batch(nodes)

        # Should group into 4 label groups
        assert len(node_queries) == 4

        # Verify all queries are valid
        for query, params in node_queries:
            assert "UNWIND" in query
            assert "MERGE" in query
            assert "SET n += props" in query
            assert "RETURN count(n) AS count" in query
            assert len(params) == 1  # One parameter set per query

        # Test relationships
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
                "from_value": "Operation Aurora",
                "to_label": "ThreatActor",
                "to_value": "APT28",
                "type": "LAUNCHED",
            },
        ]

        rel_queries = builder.merge_relationships_batch(relationships)

        # Should create 2 queries (2 different patterns)
        assert len(rel_queries) == 2

        # Verify all queries are valid
        for query, params in rel_queries:
            assert "UNWIND" in query
            assert "MATCH (from:" in query
            assert "MATCH (to:" in query
            assert "MERGE (from)-[r:" in query
            assert "RETURN count(r) AS count" in query


class TestImportServiceIntegration:
    """Integration tests for ImportService with realistic workflows."""

    def test_complete_import_workflow(self, mock_import_driver):
        """Test complete import workflow from JSON to database."""
        import_service = ImportService(mock_import_driver)

        data = {
            "metadata": {
                "version": "1.0",
                "source": "Test",
                "created": "2024-01-01T00:00:00Z",
                "description": "Test data",
            },
            "nodes": [
                {
                    "label": "ThreatActor",
                    "properties": {"name": "APT28", "type": "Nation-State"},
                },
                {
                    "label": "ThreatActor",
                    "properties": {"name": "APT29", "type": "Nation-State"},
                },
                {
                    "label": "Malware",
                    "properties": {"name": "X-Agent", "family": "Sofacy"},
                },
                {
                    "label": "Campaign",
                    "properties": {
                        "name": "Operation Aurora",
                        "start_date": "2020-01-01",
                    },
                },
            ],
            "relationships": [
                {
                    "type": "USES",
                    "from": {
                        "label": "ThreatActor",
                        "property": "name",
                        "value": "APT28",
                    },
                    "to": {"label": "Malware", "property": "name", "value": "X-Agent"},
                },
                {
                    "type": "USES",
                    "from": {
                        "label": "ThreatActor",
                        "property": "name",
                        "value": "APT29",
                    },
                    "to": {"label": "Malware", "property": "name", "value": "X-Agent"},
                },
                {
                    "type": "LAUNCHED",
                    "from": {
                        "label": "Campaign",
                        "property": "name",
                        "value": "Operation Aurora",
                    },
                    "to": {
                        "label": "ThreatActor",
                        "property": "name",
                        "value": "APT28",
                    },
                },
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            # Mock execute for all queries
            mock_import_driver.execute.side_effect = [
                [{"count": 2, "label": "ThreatActor"}],
                [{"count": 1, "label": "Malware"}],
                [{"count": 1, "label": "Campaign"}],
                [
                    {
                        "count": 2,
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

            result = import_service.import_from_json(temp_path)

            assert result.success is True
            assert result.nodes_created == 4
            assert result.relationships_created == 3
            assert result.errors == []
            assert (
                mock_import_driver.execute.call_count == 5
            )  # 3 node queries + 2 relationship queries

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_large_batch_import(self, mock_import_driver, large_dataset):
        """Test importing a larger batch of data."""
        import_service = ImportService(mock_import_driver)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(large_dataset, f)
            temp_path = f.name

        try:
            # Mock execute for the three label groups
            mock_import_driver.execute.side_effect = [
                [{"count": 20, "label": "ThreatActor"}],
                [{"count": 15, "label": "Malware"}],
                [{"count": 15, "label": "Tool"}],
            ]

            result = import_service.import_from_json(temp_path, validate=False)

            assert result.success is True
            assert result.nodes_created == 50
            assert mock_import_driver.execute.call_count == 3

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_import_with_mixed_valid_invalid_data(self, mock_import_driver):
        """Test import behavior with partially invalid data."""
        import_service = ImportService(mock_import_driver)

        data = {
            "metadata": {"version": "1.0"},
            "nodes": [
                {"label": "ThreatActor", "properties": {"name": "APT28"}},
                {"label": "InvalidLabel", "properties": {"name": "Test"}},  # Invalid
                {"label": "Malware", "properties": {"name": "X-Agent"}},
            ],
            "relationships": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            result = import_service.import_from_json(temp_path, validate=True)

            # Should fail validation due to invalid label
            assert result.success is False
            assert len(result.errors) > 0
            assert any(
                "InvalidLabel" in str(error) or "not allowed" in str(error)
                for error in result.errors
            )

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_import_performance_with_many_labels(self, mock_import_driver):
        """Test import performance with data spread across many labels."""
        import_service = ImportService(mock_import_driver)

        # Create data with 10 different labels
        nodes = []
        labels = [
            "ThreatActor",
            "Malware",
            "Tool",
            "Campaign",
            "AttackPattern",
            "Indicator",
            "Organization",
            "Vulnerability",
            "Report",
            "Incident",
        ]

        for label in labels:
            for i in range(5):
                nodes.append({"label": label, "properties": {"name": f"{label}_{i}"}})

        data = {
            "metadata": {"version": "1.0"},
            "nodes": nodes,
            "relationships": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            # Mock execute for all 10 label queries
            mock_import_driver.execute.side_effect = [
                [{"count": 5, "label": label}] for label in labels
            ]

            result = import_service.import_from_json(temp_path, validate=False)

            assert result.success is True
            assert result.nodes_created == 50
            assert mock_import_driver.execute.call_count == 10  # One per label

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_import_with_complex_relationship_patterns(self, mock_import_driver):
        """Test import with many different relationship patterns."""
        import_service = ImportService(mock_import_driver)

        data = {
            "metadata": {"version": "1.0"},
            "nodes": [
                {"label": "ThreatActor", "properties": {"name": "APT28"}},
                {"label": "Malware", "properties": {"name": "X-Agent"}},
                {"label": "Campaign", "properties": {"name": "Op Aurora"}},
                {"label": "Organization", "properties": {"name": "Acme Corp"}},
            ],
            "relationships": [
                {
                    "type": "USES",
                    "from": {
                        "label": "ThreatActor",
                        "property": "name",
                        "value": "APT28",
                    },
                    "to": {"label": "Malware", "property": "name", "value": "X-Agent"},
                },
                {
                    "type": "LAUNCHED",
                    "from": {
                        "label": "Campaign",
                        "property": "name",
                        "value": "Op Aurora",
                    },
                    "to": {
                        "label": "ThreatActor",
                        "property": "name",
                        "value": "APT28",
                    },
                },
                {
                    "type": "TARGETS",
                    "from": {
                        "label": "ThreatActor",
                        "property": "name",
                        "value": "APT28",
                    },
                    "to": {
                        "label": "Organization",
                        "property": "name",
                        "value": "Acme Corp",
                    },
                },
                {
                    "type": "INVOLVES",
                    "from": {
                        "label": "Campaign",
                        "property": "name",
                        "value": "Op Aurora",
                    },
                    "to": {"label": "Malware", "property": "name", "value": "X-Agent"},
                },
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            # Mock execute for nodes and relationships
            mock_import_driver.execute.side_effect = [
                [{"count": 1, "label": "ThreatActor"}],
                [{"count": 1, "label": "Malware"}],
                [{"count": 1, "label": "Campaign"}],
                [{"count": 1, "label": "Organization"}],
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
                [
                    {
                        "count": 1,
                        "from_label": "ThreatActor",
                        "to_label": "Organization",
                        "type": "TARGETS",
                    }
                ],
                [
                    {
                        "count": 1,
                        "from_label": "Campaign",
                        "to_label": "Malware",
                        "type": "INVOLVES",
                    }
                ],
            ]

            result = import_service.import_from_json(temp_path, validate=False)

            assert result.success is True
            assert result.nodes_created == 4
            assert result.relationships_created == 4
            # 4 node queries + 4 relationship queries
            assert mock_import_driver.execute.call_count == 8

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_dry_run_does_not_modify_database(self, mock_import_driver):
        """Test that dry run validates but doesn't execute any queries."""
        import_service = ImportService(mock_import_driver)

        data = {
            "metadata": {"version": "1.0"},
            "nodes": [
                {"label": "ThreatActor", "properties": {"name": "APT28"}},
            ],
            "relationships": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            result = import_service.import_from_json(temp_path, dry_run=True)

            assert result.success is True
            assert result.nodes_created == 0
            assert result.relationships_created == 0
            # Verify no database operations were executed
            assert mock_import_driver.execute.call_count == 0

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_import_preserves_node_properties(self, mock_import_driver):
        """Test that all node properties are preserved during import."""
        import_service = ImportService(mock_import_driver)

        data = {
            "metadata": {"version": "1.0"},
            "nodes": [
                {
                    "label": "ThreatActor",
                    "properties": {
                        "name": "APT28",
                        "type": "Nation-State",
                        "motivation": "Espionage",
                        "aliases": "Fancy Bear",
                        "first_seen": "2015-01-01",
                        "last_seen": "2024-01-01",
                    },
                },
            ],
            "relationships": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            mock_import_driver.execute.return_value = [
                {"count": 1, "label": "ThreatActor"}
            ]

            result = import_service.import_from_json(temp_path, validate=False)

            assert result.success is True

            # Verify the query was called with all properties
            call_args = mock_import_driver.execute.call_args
            query, params = call_args[0]

            # Check that all properties were included in parameters
            node_data = params["nodes_ThreatActor"][0]
            assert node_data["name"] == "APT28"
            assert node_data["type"] == "Nation-State"
            assert node_data["motivation"] == "Espionage"
            assert node_data["aliases"] == "Fancy Bear"
            assert node_data["first_seen"] == "2015-01-01"
            assert node_data["last_seen"] == "2024-01-01"

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_import_with_relationship_properties(self, mock_import_driver):
        """Test that relationship properties are preserved during import."""
        import_service = ImportService(mock_import_driver)

        data = {
            "metadata": {"version": "1.0"},
            "nodes": [
                {"label": "ThreatActor", "properties": {"name": "APT28"}},
                {"label": "Malware", "properties": {"name": "X-Agent"}},
            ],
            "relationships": [
                {
                    "type": "USES",
                    "from": {
                        "label": "ThreatActor",
                        "property": "name",
                        "value": "APT28",
                    },
                    "to": {"label": "Malware", "property": "name", "value": "X-Agent"},
                    "properties": {
                        "source": "Report 123",
                        "first_seen": "2020-01-01",
                        "last_seen": "2024-01-01",
                        "description": "APT28 uses X-Agent malware",
                    },
                },
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
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

            result = import_service.import_from_json(temp_path, validate=False)

            assert result.success is True

            # Verify relationship properties were included
            # The third call should be for the relationship
            rel_call = mock_import_driver.execute.call_args_list[2]
            query, params = rel_call[0]

            rel_data = params["rels_ThreatActor_USES_Malware"][0]
            assert rel_data["properties"]["source"] == "Report 123"
            assert rel_data["properties"]["first_seen"] == "2020-01-01"
            assert rel_data["properties"]["last_seen"] == "2024-01-01"
            assert rel_data["properties"]["description"] == "APT28 uses X-Agent malware"

        finally:
            Path(temp_path).unlink(missing_ok=True)

#!/usr/bin/env python3
"""CLI script for importing threat intelligence data into Neo4j.

This script provides a command-line interface for importing JSON data files
into the Neo4j database. It uses the ImportService for all import logic.

Usage:
    python import_data.py data/demo_data.json
    python import_data.py data/demo_data.json --validate --dry-run
    python import_data.py data/demo_data.json --no-validate --verbose
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from driver import GraphDBDriver
from services.import_service import ImportService


def print_banner():
    """Print application banner."""
    print("=" * 70)
    print("  Threat Intelligence Data Importer")
    print("  Import JSON data into Neo4j database")
    print("=" * 70)
    print()


def print_result_summary(result):
    """Print import result summary.

    Args:
        result: ImportResult object.
    """
    print()
    print("=" * 70)
    print("IMPORT SUMMARY")
    print("=" * 70)

    # Status
    if result.success:
        print("Status: SUCCESS")
    else:
        print("Status: FAILED")

    print()

    # Statistics
    print("Statistics:")
    print(f"  Nodes created/merged:         {result.nodes_created}")
    print(f"  Relationships created/merged: {result.relationships_created}")
    print(f"  Duration:                     {result.duration_seconds:.2f}s")

    # Metadata
    if result.metadata:
        print()
        print("Source Metadata:")
        print(f"  Version:      {result.metadata.get('version', 'N/A')}")
        print(f"  Source:       {result.metadata.get('source', 'N/A')}")
        print(f"  Created:      {result.metadata.get('created', 'N/A')}")
        if "description" in result.metadata:
            desc = result.metadata["description"]
            if len(desc) > 60:
                desc = desc[:57] + "..."
            print(f"  Description:  {desc}")

    # Warnings
    if result.warnings:
        print()
        print(f"Warnings ({len(result.warnings)}):")
        for i, warning in enumerate(result.warnings[:5], 1):
            print(f"  {i}. {warning}")
        if len(result.warnings) > 5:
            print(f"  ... and {len(result.warnings) - 5} more warnings")

    # Errors
    if result.errors:
        print()
        print(f"Errors ({len(result.errors)}):")
        for i, error in enumerate(result.errors[:10], 1):
            print(f"  {i}. {error}")
        if len(result.errors) > 10:
            print(f"  ... and {len(result.errors) - 10} more errors")

    print("=" * 70)


def main():
    """Main entry point for CLI script."""
    parser = argparse.ArgumentParser(
        description="Import threat intelligence data from JSON into Neo4j",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic import
  python import_data.py data/demo_data.json

  # Import with validation (default)
  python import_data.py data/demo_data.json --validate

  # Dry run (validate only, don't import)
  python import_data.py data/demo_data.json --dry-run

  # Skip validation (faster, but risky)
  python import_data.py data/demo_data.json --no-validate

  # Verbose output
  python import_data.py data/demo_data.json --verbose

  # Custom Neo4j connection
  NEO4J_URI=bolt://localhost:7687 \\
  NEO4J_USER=neo4j \\
  NEO4J_PASSWORD=mypassword \\
  python import_data.py data/demo_data.json

Environment Variables:
  NEO4J_URI       Neo4j connection URI (default: bolt://localhost:7687)
  NEO4J_USER      Neo4j username (default: neo4j)
  NEO4J_PASSWORD  Neo4j password (default: password)
        """,
    )

    # Positional arguments
    parser.add_argument(
        "json_file",
        type=str,
        help="Path to JSON file containing threat intelligence data",
    )

    # Optional arguments
    parser.add_argument(
        "--validate",
        action="store_true",
        default=True,
        help="Validate data before import (default: enabled)",
    )
    parser.add_argument(
        "--no-validate", action="store_true", help="Skip validation (faster but risky)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate only, don't import data"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output (DEBUG level)"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Minimal output (errors only)"
    )

    args = parser.parse_args()

    # Handle --no-validate flag
    validate = args.validate and not args.no_validate

    # Set log level
    if args.verbose:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.ERROR
    else:
        log_level = logging.INFO

    # Print banner (unless quiet)
    if not args.quiet:
        print_banner()

    # Check if file exists
    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"Error: File not found: {args.json_file}")
        return 1

    # Get Neo4j connection parameters from environment
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    # Print configuration (unless quiet)
    if not args.quiet:
        print("Configuration:")
        print(f"  Input file:  {json_path.absolute()}")
        print(f"  Neo4j URI:   {neo4j_uri}")
        print(f"  Neo4j user:  {neo4j_user}")
        print(f"  Validation:  {'enabled' if validate else 'disabled'}")
        print(f"  Dry run:     {'yes' if args.dry_run else 'no'}")
        print()

    # Initialize database connection
    try:
        if not args.quiet:
            print("Connecting to Neo4j...")

        driver = GraphDBDriver(
            uri=neo4j_uri, user=neo4j_user, password=neo4j_password, log_level=log_level
        )

        # Test connection
        result = driver.run_safe_query("RETURN 1 AS test")
        if not result.success:
            print(f"Failed to connect to Neo4j: {result.error}")
            return 1

        if not args.quiet:
            print("Connected to Neo4j")
            print()

    except Exception as e:
        print(f"Database connection error: {e}")
        return 1

    # Initialize import service
    importer = ImportService(driver, log_level=log_level)

    # Perform import
    try:
        result = importer.import_from_json(
            filepath=str(json_path), validate=validate, dry_run=args.dry_run
        )

        # Print summary (unless quiet)
        if not args.quiet:
            print_result_summary(result)
        elif not result.success:
            # Print errors even in quiet mode
            print(f"Import failed with {len(result.errors)} errors")
            for error in result.errors[:3]:
                print(f"  - {error}")

        # Return appropriate exit code
        return 0 if result.success else 1

    except KeyboardInterrupt:
        print("\n\nImport interrupted by user")
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        print(f"\nUnexpected error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    finally:
        # Close database connection
        driver.close()


if __name__ == "__main__":
    sys.exit(main())

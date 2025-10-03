from src.driver import GraphDBDriver
import pytest

"""
This file contains the tests for the driver.
Run pytest in the terminal.
"""


def test_connect():
    db = GraphDBDriver("neo4j://localhost:7687", "neo4j", "StronkP4ssword", 10)
    assert type(db) is GraphDBDriver
    assert db.connect() == "connected"
    db.close()

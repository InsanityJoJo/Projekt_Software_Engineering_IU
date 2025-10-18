"""Main backend entry point.

This module initializes the Neo4j database
"""

from driver import GraphDBDriver
import time

service = GraphDBDriver("neo4j://localhost:7687", "neo4j", "password", 10)

service.connect()
print("Neo4j is running – http://localhost:7474")
time.sleep(60)

service.close()

from neo4j import GraphDatabase
import logging
from logger import setup_logger

"""
This is the driver-module for the neo4j-db
"""


class GraphDBDriver:
    def __init__(self, uri, user, password, log_level=logging.INFO):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.logger = setup_logger("GraphDBDriver", log_level)
        self.logger.info("Neo4j driver initialized.")

    def connect(self):
        return "connected"

    def close(self):
        self.driver.close()
        self.logger.info("Neo4j driver closed.")

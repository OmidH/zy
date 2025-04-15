from neo4j import GraphDatabase
from ...helper.logger import getLogger

logging = getLogger()


class Neo4jDBSingleton:
    _instance = None
    _driver = None
    _uri = "bolt://localhost:7687"  # Die URI des Neo4j-Servers
    _user = "neo4j"  # Neo4j-Benutzername
    _password = "easypw123"  # Neo4j-Passwort

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Neo4jDBSingleton, cls).__new__(cls, *args, **kwargs)
            cls._instance._driver = GraphDatabase.driver(cls._instance._uri, auth=(cls._instance._user, cls._instance._password))
        return cls._instance

    def close(self):
        self._driver.close()

    def query(self, query, parameters=None):
        logging.info(f"neo4j - query - {query}")
        with self._driver.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]

    def execute_queries(self, queries):
        with self._driver.session() as session:
            for query in queries:
                session.run(query)

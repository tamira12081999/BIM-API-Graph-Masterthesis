import os
from dotenv import load_dotenv
load_dotenv()
from langchain_neo4j import Neo4jGraph

#Chatbot-Graph
NEO4J_URI = os.getenv("NEO4J_URI_B", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME_B", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD_B", "your_password")
#Name of the connected graph:
graph = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USER,
    password=NEO4J_PASSWORD,
    )

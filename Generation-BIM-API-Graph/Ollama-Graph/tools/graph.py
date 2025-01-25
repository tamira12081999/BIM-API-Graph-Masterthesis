import os
from dotenv import load_dotenv
load_dotenv()
from langchain_community.graphs import Neo4jGraph

#Chatbot-Graph
NEO4J_URI_VS = os.getenv('NEO4J_URI_VS')
NEO4J_USERNAME_VS = os.getenv('NEO4J_USERNAME_VS')
NEO4J_PASSWORD_VS = os.getenv('NEO4J_PASSWORD_VS')
#Name of the connected graph:
vs_graph = Neo4jGraph(
    url=NEO4J_URI_VS,
    username=NEO4J_USERNAME_VS,
    password=NEO4J_PASSWORD_VS,
    )

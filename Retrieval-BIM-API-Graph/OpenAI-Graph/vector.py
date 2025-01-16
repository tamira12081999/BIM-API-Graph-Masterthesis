import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j_graphrag.generation import RagTemplate
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.embeddings.openai import OpenAIEmbeddings
from neo4j_graphrag.generation.graphrag import GraphRAG
from neo4j_graphrag.retrievers import VectorCypherRetriever, VectorRetriever

# Load environment variables
load_dotenv()

# Setup Neo4j driver
NEO4J_URI = os.getenv("NEO4J_URI_OPENAI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME_OPENAI", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD_OPENAI", "your_password")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Configure LLM
llm = OpenAILLM(
    model_name="gpt-4o-mini",
    model_params={
        "temperature": 0  # Lower temperature for deterministic output
    }
)
# Initialize embedding model
embedder = OpenAIEmbeddings(
    api_key=os.getenv("OPENAI_API_KEY"),  # Ensure API key is correctly loaded
    model="text-embedding-ada-002"
)
#Vector-Retriever
vector_retriever = VectorRetriever(
    driver=driver,
    index_name="text_embeddings",
    embedder=embedder,
    return_properties=["text"]
)

# RAG template
rag_template = RagTemplate(
    template='''Answer the Question using the following Context. Only respond with information mentioned in the Context.

# Question:
{query_text}

# Context:
{context}

# Answer:
''', expected_inputs=['query_text', 'context']
)

# Initialize GraphRAG
vector_rag = GraphRAG(llm=llm, retriever=vector_retriever, prompt_template=rag_template)

def vectorRAG (q):
    print("vectorRAG")
    print(f"Received query: {q}")
    result = vector_rag.search(q, retriever_config={'top_k': 5}).answer
    return result
# Example Query
# query = ("What are the input parameters and the return type of function Centroid3D?")
# try:
#     print("VECTOR")
#     print(vector_rag.search(query, retriever_config={'top_k': 5}).answer)
#
# except Exception as e:
#     print(f"Error during query: {e}")
# answer = vectorRAG("What are the input parameters and the return type of function Centroid3D?")
# print (answer)
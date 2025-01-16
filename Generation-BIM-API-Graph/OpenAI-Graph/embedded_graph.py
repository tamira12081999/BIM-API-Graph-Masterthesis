# Import required libraries
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from pathlib import Path

# Import Neo4j GraphRAG components
from neo4j_graphrag.generation import RagTemplate
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.embeddings.openai import OpenAIEmbeddings
from neo4j_graphrag.generation.graphrag import GraphRAG
from neo4j_graphrag.experimental.components.text_splitters.fixed_size_splitter import FixedSizeSplitter
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.retrievers import VectorCypherRetriever, VectorRetriever
from neo4j_graphrag.indexes import create_vector_index


# Load environment variables
load_dotenv()

# Setup Neo4j driver
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Configure LLM
llm = OpenAILLM(
    model_name="gpt-4o-mini",
    model_params={

        "temperature": 0  # Lower temperature for deterministic output
    }
)
# Initialize embedding model
# embedder = OpenAIEmbeddings()
embedder = OpenAIEmbeddings(
    api_key=os.getenv("OPENAI_API_KEY"),  # Ensure API key is correctly loaded
    model="text-embedding-ada-002"
)
# Define node labels
basic_node_labels = ["Function", "Category", "Datatype", "Parameter", "Document" ]
function_node_labels = ["ReturnType", "DataType", "Datatype", "Parameter", "Document" ]


node_labels = basic_node_labels + function_node_labels

# Define relationship types
rel_types = [
    "HAS_PARAMETER", "FUNCTION_OF", "BELONGS_TO", "RETURNS_DATATYPE",
    "IS_DATATYPE", "RETURNS", "USES"
]


# Define prompt template
prompt_template = '''
You are a BIM-API researcher tasked with extracting information from text documentations
and structuring it in a property graph to inform further research Q&A.

Extract the entities (nodes) and specify their type from the following Input text.
Also extract the relationships between these nodes. The relationship direction goes from the start node to the end node.

Return the result as JSON using the following format:
{{
    "nodes": [
        {{"id": "0", "label": "the type of entity", "properties": {{"name": "name of entity"}} }}
    ],
    "relationships": [
        {{"type": "TYPE_OF_RELATIONSHIP", "start_node_id": "0", "end_node_id": "1", "properties": {{"details": "Description of the relationship"}} }}
    ]
}}

Use only the following nodes and relationships:
{schema}

Input text:
{text}
'''

# Initialize the knowledge graph builder
DOCS_PATH = os.getenv('DOCS_PATH', '.')
file_path_txt = Path(DOCS_PATH) / 'data/vs-short.txt'
print(file_path_txt.exists())
kg_builder = SimpleKGPipeline(
    llm=llm,
    driver=driver,
    text_splitter=FixedSizeSplitter(chunk_size=500, chunk_overlap=100),
    embedder=embedder,
    prompt_template=prompt_template,
    entities=node_labels,
    relations=rel_types,
    from_pdf=False
)

import asyncio

async def process_document():
    try:
        with open(file_path_txt, 'r', encoding='utf-8') as file:
            text_content = file.read()
        print(f"Processing: {file_path_txt}")
        result = await kg_builder.run_async(text=text_content)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error processing document: {e}")

asyncio.run(process_document())

# Create vector index
create_vector_index(
    driver,
    name="text_embeddings",
    label="Chunk",
    embedding_property="embedding",
    dimensions=1536,
    similarity_fn="cosine"
)

# Initialize retrievers
vector_retriever = VectorRetriever(
    driver=driver,
    index_name="text_embeddings",
    embedder=embedder,
    return_properties=["text"]
)

graph_retriever = VectorCypherRetriever(
    driver=driver,
    index_name="text_embeddings",
    embedder=embedder,
    retrieval_query="""
    MATCH (chunk)<-[:FROM_CHUNK]-(entity)-[relList:!FROM_CHUNK]-{1,2}(nb)
    UNWIND relList AS rel
    WITH collect(DISTINCT chunk) AS chunks, collect(DISTINCT rel) AS rels
    RETURN apoc.text.join([c IN chunks | c.text], '\n') +
        apoc.text.join([r IN rels |
        startNode(r).name+' - '+type(r)+' '+r.details+' -> '+endNode(r).name],
        '\n') AS info
    """
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
graph_rag = GraphRAG(llm=llm, retriever=graph_retriever, prompt_template=rag_template)

# Example Query
query = "Can you summarize Abs function including parameters and category?"
try:
    print("VECTOR")
    print(vector_rag.search(query, retriever_config={'top_k': 5}).answer)
    print("GRAPH")
    print(graph_rag.search(query, retriever_config={'top_k': 5}).answer)
except Exception as e:
    print(f"Error during query: {e}")

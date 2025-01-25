import os
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
import json
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

from sqlalchemy import values

load_dotenv()
# from tools import llm
from langchain_core.prompts.base import PromptValue

from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain.prompts import PromptTemplate
from langchain_ollama import ChatOllama

llm = ChatOllama(
    model= "llama3.2:latest",
    temperature=0,
    )
llmO = ChatOpenAI(
    openai_api_key=os.getenv('OPENAI_API_KEY'),
    model="gpt-4o-mini"
)
#Chatbot-Graph
NEO4J_URI_VS = os.getenv('NEO4J_URI_VS')
NEO4J_USERNAME_VS = os.getenv('NEO4J_USERNAME_VS')
NEO4J_PASSWORD_VS = os.getenv('NEO4J_PASSWORD_VS')
#Name of the connected graph:
graph = Neo4jGraph(
    url=NEO4J_URI_VS,
    username=NEO4J_USERNAME_VS,
    password=NEO4J_PASSWORD_VS,
    )

CYPHER_GENERATION_TEMPLATE = """Task:Generate Cypher statement to query a graph database.
Instructions:
Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided.
Only include the generated Cypher statement in your response.

Always use case insensitive search when matching strings.

You must always include a RETURN statement. 
You must only use Relationships provided in the schema.
Schema:
{schema}


------------
The question is:
{question}"""

cypher_generation_prompt = PromptTemplate(
    template=CYPHER_GENERATION_TEMPLATE,
    input_variables=["schema", "question"],
)
cypher_chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    cypher_prompt=cypher_generation_prompt,
    verbose=True,
    allow_dangerous_requests=True,
    enhanced_schema=True,
    validate_cypher=True,
    top_k=10,
    return_direct=True, # Directly return the Cypher query results

)

chain = cypher_chain | llm | StrOutputParser()

def run_cypher(q):
    # Perform the query and return the result
    print("run_cypher")
    print(f"Received query: {q}")
    # Run the cypher chain
    result = cypher_chain.invoke(q)
    # return result
    # Debug output
    # print("Generated Result:", result)
    #

    def extract_key_values(data, key_patterns):
        extracted_values = []
        if isinstance(data, dict):
            for key, value in data.items():
                # Match key against key_patterns
                if key in key_patterns:
                    extracted_values.append(value)
                elif isinstance(value, (dict, list)):
                    extracted_values.extend(extract_key_values(value, key_patterns))
        elif isinstance(data, list):
            for item in data:
                extracted_values.extend(extract_key_values(item, key_patterns))
        return extracted_values

    # Define key patterns to search for
    key_patterns = ['p.name', 'c.name', 'n.name', 'name', 'f.name', 'd.name',]  # Add more patterns as needed

    # Extract values matching any of the key patterns
    extracted_values = extract_key_values(result.get('result', []), key_patterns)

    # print("Extracted Values:", extracted_values)
    return extracted_values



# a = run_cypher("what Parameters has Abs?")
# print("a: ", a)
# b = run_cypher("List all nodes belonging to Category Worksheets.")
# print("b: ", b)
# c = run_cypher("List all nodes belonging to Textures.")
# print("c: ", c)
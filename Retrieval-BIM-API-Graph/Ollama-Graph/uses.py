import os
from dotenv import load_dotenv

load_dotenv()
from tools import llm

from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain.prompts import PromptTemplate

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
Use only the provided relationship type [USES] and properties in the schema.
Do not use any other relationship types or properties that are not provided.
Only include the generated Cypher statement in your response.
Return the list of FunctionUsed.
Always use case insensitive search when matching strings.
Always generate a individual Cypher query for each word in the input. 
You must always include a RETURN statement. 
Schema:
{schema}

Examples: 

# Find functions connected to a first function (by name case insensitive) using the [USES] relation
MATCH (f:Function)
MATCH (f)-[r:USES]->(f2:Function)-[r2:USES]->(f3:Function)
RETURN f.name AS FunctionName, r.page_url AS url, f2 AS FunctionUsed, r2.page_url AS Url2, f3 AS FunctionUsed2


The question is:
{question}"""

cypher_generation_prompt = PromptTemplate(
    template=CYPHER_GENERATION_TEMPLATE,
    input_variables=["schema", "question"],
)

cypher_chain = GraphCypherQAChain.from_llm(
    llm.llm,
    graph=graph,
    cypher_prompt=cypher_generation_prompt,
    verbose=True,
    allow_dangerous_requests=True,
    enhanced_schema=True,
    return_direct=True
)


def run_uses(q):
    # Perform the query and return the result
    print("run_uses", q)
    result = cypher_chain.invoke(q)
    # print("result", result)
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
    key_patterns = ['p.name', 'c.name', 'n.name', 'name', 'f.name', 'd.name', 'url', 'FunctionUsed','ParameterName']  # Add more patterns as needed

    # Extract values matching any of the key patterns
    extracted_values = extract_key_values(result.get('result', []), key_patterns)
    return extracted_values
    # functions_used = []
    # for item in result.get('result', []):  # Access the 'result' key, which is a list
    #     function_used = item.get('FunctionUsed')  # Access the FunctionUsed dictionary
    #     print("functions_used",functions_used)
    #     if function_used and 'name' in function_used:
    #         functions_used.append(function_used['name'])  # Append the name to the list
    #     url = item.get('Url', None)
    #     if url:
    #         functions_used.append(url)
    # print("functions_used", functions_used)
    #
    # return functions_used

# b = run_uses("CreateResizableLayout")
# print("b", b)
# a = run_uses("CreateLayout")
# print("a",a)
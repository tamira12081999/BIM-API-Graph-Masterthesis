import os
import json
from dotenv import load_dotenv
from pathlib import Path
from neo4j import GraphDatabase
from .graph import vs_graph

# Load environment variables
load_dotenv()

# Default folder path from environment variable
DOCS_PATH = os.getenv('DOCS_PATH')
default_input_path = Path(DOCS_PATH) / 'vs-knowledge-graph/data/vs.json'


def load_and_process_json(input_path):
    """
    Load and process a JSON file to create or merge nodes in the Neo4j database.
    """
    # Load JSON file directly
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Process each item in the JSON list
    for item in data:
        # Extract properties from JSON
        function_id = item['id']
        function_name = item.get("FunctionName", "")
        return_type = item.get("Return", "None")
        return_description = item.get("ReturnDescription", "")
        description = item.get("description", "null")
        python_code = item.get("Python", "null")
        vector_script = item.get("VectorScript", "null")
        category = item.get("Category", "null")
        filename = input_path.name

        # Prepare input parameters
        input_parameters = item.get("InputParameters", None)
        if isinstance(input_parameters, dict):
            input_parameters = [input_parameters]
        elif isinstance(input_parameters, str):
            input_parameters = [{"name": input_parameters, "datatype": "null", "description": "null"}]
        elif input_parameters is None:
            input_parameters = []

        # Prepare properties for graph query
        properties = {
            "filename": filename,
            "function_id": function_id,
            "function_name": function_name,
            "return_type": return_type,
            "return_description": return_description,
            "description": description,
            "python": python_code,
            "vector_script": vector_script,
            "category": category,
        }
        create_or_merge_nodes(properties)
        # Process parameters for the function
        for param in input_parameters:
            add_parameter_node(param, function_name)


def create_or_merge_nodes(properties):
    """
    Create or merge nodes in the Neo4j database for a function and its metadata.
    """
    vs_graph.query("""
        MERGE (d:Document {id: $filename})
        MERGE (f:Function {name: $function_name})
        ON CREATE SET f.return = COALESCE($return_type, "None"),
                      f.function_id = $function_id, 
                      f.description = $description, 
                      f.python = $python, 
                      f.vector_script = $vector_script
        MERGE (cat:Category {name: $category})
        MERGE (d)<-[:FUNCTION_OF]-(f)
        MERGE (f)-[:BELONGS_TO]->(cat)
        MERGE (data:Datatype {name: $return_type})
        ON CREATE SET data.returnDescription = COALESCE($return_description, "None")
        MERGE (f)-[:RETURNS_DATATYPE]->(data)
    """, properties)


def add_parameter_node(param, function_name):
    """
    Add a parameter node to the Neo4j database and link it to its function and datatype.
    """
    # Extract parameter properties
    param_name = param.get("name")
    param_datatype = param.get("datatype", "null")
    param_description = param.get("description", "null")

    # Prepare parameter properties
    parameter_properties = {
        "param_name": param_name,
        "param_datatype": param_datatype,
        "param_description": param_description,
        "function_name": function_name,
    }

    # Execute Neo4j query for parameter
    vs_graph.query("""
        MERGE (p:Parameter {name: $param_name})
        ON CREATE SET p.datatype = $param_datatype, 
                      p.description = $param_description
        MERGE (d:Datatype {name: $param_datatype})
        MERGE (f:Function {name: $function_name})
        MERGE (f)-[:HAS_PARAMETER]->(p)
        MERGE (p)-[:IS_DATATYPE]->(d)
    """, parameter_properties)


# Callable function for external use
def process_json_file(input_file=None):
    """
    Process the specified JSON file or the default one and load its data into the Neo4j database.
    """
    if not input_file:
        input_file = default_input_path
    load_and_process_json(input_file)

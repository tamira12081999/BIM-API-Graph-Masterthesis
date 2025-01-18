import requests
from bs4 import BeautifulSoup
import re
import json
from langchain_community.graphs import Neo4jGraph

from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()

# Default path for documents
DOCS_PATH = os.getenv('DOCS_PATH')
output_cypher_path = Path(DOCS_PATH) / 'data/cypher_queries.json'
#Chatbot-Graph
NEO4J_URI = os.getenv('NEO4J_URI_B')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME_B')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD_B')
#Name of the connected graph:
graph = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USERNAME,
    password=NEO4J_PASSWORD,
    )

# Define a list of names to filter
NAMES_TO_FILTER = ["ActiveClass"
"ActLayer"
"ActSSheet"
"ActSymDef"
"ActSymDefN"
"Add2DVertex"
"Add3DPt"
"BeginPoly3D"
"EndPoly3D"
"AddAssociation"
"AddButtonMode"
"AddCavity"
"AddChoice"
"AddCustomTexPart"
"AddHole"
"Wall"
"WallArea_Gross"
"WallArea_Net"
"WallAverageHeight"
"WallCap"
"WallFootPrint"
"WallHeight"
"WallPeak"
"WallThickness"
"WallTo"
"WallWidth"
"WebDlgEnableConsole"
"nableConsole"
"Width"
"BeginRoof"
"vs.BeginRoof"
"GetRoofAttributes"
"GetRoofEdge"
"GetRoofElementType"
"GetRoofFaceAttrib"
"GetRoofFaceCoords"
"GetRoofPreferences"
"GetRoofPrefStyle"
"HANDLE"
"GetRoofStyle"
"GetRoofVertices"
"GetRoundingBase"
"CreateRoof"
"ateRoof"
"CreateRoofStyle"
"Create Roof Style"]  # Replace with the actual names you want to filter for

# Function to scrape relevant links from the main page
def get_all_links(base_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    response = requests.get(base_url, headers=headers)
    print(f"Fetching {base_url} - Status Code: {response.status_code}")
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('http'):
            full_url = href
        elif href.startswith('/'):
            full_url = f"https://developer.vectorworks.net{href}"
        else:
            continue

        if "index.php?title=VS:" in full_url and not any(
            ignore in full_url
            for ignore in ["Special:", "Categories", "Main_Page", "UserLogin"]
        ):
            links.append(full_url)

    return links

# Function to extract Python examples and functions
# Updated function to extract Python examples and filter by names
def extract_python_examples(page_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    response = requests.get(page_url, headers=headers)
    print(f"Processing {page_url} - Status Code: {response.status_code}")
    if response.status_code != 200:
        return set()

    soup = BeautifulSoup(response.text, 'html.parser')
    page_text = soup.get_text().lower()

    # Check if any of the specified names are present in the page
    if not any(name.lower() in page_text for name in NAMES_TO_FILTER):
        print(f"Skipping {page_url} as it does not contain specified names.")
        return set()

    code_blocks = soup.find_all('pre')
    examples = []

    for block in code_blocks:
        if 'Python' in block.text.lower() or 'vs.' in block.text:
            examples.append(block.text)

    if not examples:
        print(f"No Python examples found on {page_url}")
        return set()

    functions = set(re.findall(r'vs\.\w+', ' '.join(examples)))
    return functions

# Function to generate Cypher queries
def generate_cypher_queries(base_function, related_functions, page_url):
    cypher_queries = []
    base_function_name = base_function.replace("VS:", "")
    for func in related_functions:
        related_function_name = func.replace("vs.", "").replace(" ", "_")
        if base_function_name != related_function_name:
            query = (
                f"MERGE (f1:Function {{name: '{base_function_name}'}}) "
                f"MERGE (f2:Function {{name: '{related_function_name}'}}) "
                f"MERGE (f1)-[:USES {{page_url: '{page_url}'}}]->(f2);"
            )
            cypher_queries.append(query)
    return cypher_queries

# Function to store connections
def store_connections(base_function, related_functions):
    connections = []
    base_function_name = base_function.replace("VS:", "")
    for func in related_functions:
        related_function_name = func.replace("vs.", "").replace(" ", "_")
        if base_function_name != related_function_name:
            connections.append((base_function_name, related_function_name))
    return connections

# Main process
# Main process remains mostly the same
def scrape_and_generate_queries(base_url, output_cypher):
    links = get_all_links(base_url)
    if not links:
        print("No relevant links found. Exiting.")
        return

    cypher_queries = []
    connections = []

    for link in links:
        functions = extract_python_examples(link)
        if functions:
            current_page_function = link.split('=')[-1]
            connections.extend(store_connections(current_page_function, functions))
            cypher_queries.extend(generate_cypher_queries(current_page_function, functions, link))

    with open(output_cypher, "w") as file:
        json.dump(cypher_queries, file)

    print(f"Saved {len(cypher_queries)} Cypher queries to {output_cypher}")
    return connections, cypher_queries

# Function to add queries to the graph
def add_queries_to_graph(cypher_path):
    with open(cypher_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for item in data:
        print(f"Executing query: {item}")
        graph.query(item)

# Entry point for external calls
def run_webpage(base_url, cypher_path=output_cypher_path):
    connections, cypher_queries = scrape_and_generate_queries(base_url, cypher_path)
    add_queries_to_graph(cypher_path)
    return connections, cypher_queries

# Ensure the script runs only when executed directly
if __name__ == "__main__":
    BASE_URL = "https://developer.vectorworks.net/index.php?title=VS:Function_Reference"
    CYPHER_PATH = Path(DOCS_PATH) / 'data/cypher_queries.json'
    run_webpage(BASE_URL, CYPHER_PATH)

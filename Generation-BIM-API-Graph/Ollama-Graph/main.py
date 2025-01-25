# Import
import json
import re
from pathlib import Path
import os
from dotenv import load_dotenv
from tools.txt_to_json import run_extraction
from tools.deterministic_kg import process_json_file
from tools.embedded_kg import run_embedded
from tools.webpage_kg import run_webpage
### load variables ###
load_dotenv()
DOCS_PATH = os.getenv('DOCS_PATH')
file_path_txt = Path(DOCS_PATH) / 'data/vs.txt'
file_path_json = Path(DOCS_PATH) / 'data/vs.json'
output_cypher_path = Path(DOCS_PATH) / 'data/cypher_queries.json'
BASE_URL = "https://developer.vectorworks.net/index.php?title=VS:Function_Reference"
CYPHER_PATH = Path(DOCS_PATH) / 'data/cypher_queries.json'

def main():
    try:
        # Step 1: Convert .txt to .json
        print("Start: Convert .txt to .json")
        run_extraction(file_path_txt, file_path_json)
        print("Finished: Convert .txt to .json")

        # Step 2: Create KG with deterministic approach
        print("Start: Create KG with deterministic approach")
        process_json_file(file_path_json)
        print("Finished: Create KG with deterministic approach")

        # Step 3: Create KG with LLM embeddings
        print("Start: Create KG with LLM embeddings")
        run_embedded(file_path_txt)
        print("Finished: Create KG with LLM embeddings")

        # Step 4: Add examples from the webpage
        print("Start: Scraping and processing webpage data")
        connections, queries = run_webpage(BASE_URL, CYPHER_PATH)

        # Output results
        print(f"Connections: {connections}")
        print(f"Generated Queries: {queries}")
        print("Finished: Scraping and processing webpage data")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
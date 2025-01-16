# Import
import json
import re
from pathlib import Path
import os
from dotenv import load_dotenv
from txtToJson import run_extraction

### load variables ###
load_dotenv()
DOCS_PATH = os.getenv('DOCS_PATH')
print(DOCS_PATH)
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


    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
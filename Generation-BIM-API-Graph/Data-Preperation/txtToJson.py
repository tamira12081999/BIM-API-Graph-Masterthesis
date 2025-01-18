import json
import re
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()
DOCS_PATH = os.getenv('DOCS_PATH')
file_path = Path(DOCS_PATH) / 'data/vs-Approach-B.txt'
output_path = Path(DOCS_PATH) / 'data/vs-Approach-B.json'

"""Keywords for extraction line"""
keyword_split_function = "\ndef "
keyword_split_function_start = "def "

keyword_category = "Category:"
keyword_return = "return "


def extract_description(function_lines):
    """Extract description following the 'Category:' tag in comments."""
    description = []
    capture = False
    for line in function_lines:
        stripped_line = line.strip()
        if keyword_category in stripped_line:
            capture = True  # Start capturing description after 'Category:'
            continue
        if capture:
            if stripped_line.startswith("'''") or stripped_line == "":
                break  # Stop capturing when triple quotes or empty line is found
            description.append(stripped_line)
    return " ".join(description)


def extract_return_value(function_lines):
    """Extract the return value and description from the function body, handling multi-line returns."""
    return_lines = []
    capture = False
    for line in function_lines:
        stripped_line = line.strip()
        if stripped_line.startswith(keyword_return):
            capture = True
            return_lines.append(stripped_line.split(keyword_return, 1)[1].strip())
            continue
        if capture:
            return_lines.append(stripped_line)
            if stripped_line.endswith(")"):
                break

    # Join all lines into a single return value
    return_value = " ".join(return_lines).strip() if return_lines else None

    # Remove quotes from return value
    if return_value:
        return_value = return_value.replace("'", "")

    # Split return value and description for multiline or single-line return
    if return_value:
        if '#' in return_value:
            # Extract everything before '#' as return value, and everything after as the description
            return_type, return_description = return_value.split('#', 1)
            return return_type.strip(), return_description.strip()
        else:
            return return_value, None

    return return_value, None


def extract_key_value(line):
    """Extract key-value pairs from lines of code or comments."""
    if ':' in line:
        key, value = line.split(':', 1)
        key, value = key.strip(), value.strip()

        # Ignore invalid keys that may be misinterpreted
        if key not in {"(", ")"} and not key.startswith("def ") and not key.startswith(
                keyword_return):  # Filter out stray parentheses or other invalid keys
            return key, value
    return None, None


def extract_datatype_description(comment):
    """
      Split the comment into datatype and description.
      Example: "in/out HANDLE - A 2D object to be cut by [[p:2]]."
      Handles cases where datatype or description may be missing.
      """
    # Split comment by ' - ' to get datatype and description
    if ' - ' in comment:
        datatype, description = comment.split(' - ', 1)
        return datatype.strip(), description.strip()
    # Default if there's no clear split between datatype and description
    return comment.strip(), ""


def extract_parameters(param_line, following_lines):
    parameters = []
    param_pattern = re.compile(r'(\w+)\s*,?\s*#\s*([\w/\[\]\(\)\s]+)(?:\s*-\s*(.*))?')

    # Inline parameters in the first line, if present
    if param_line.strip():
        params = param_line.split(',')
        for param in params:
            param_name = param.strip()
            if param_name:
                parameters.append({
                    "name": param_name,
                    "datatype": "",
                    "description": ""
                })

    # Process multi-line parameters
    for line in following_lines:
        stripped_line = line.strip()

        # Skip lines that are return statements or invalid parameter lines
        if stripped_line.startswith('return') or not '#' in stripped_line or stripped_line.startswith(')'):
            continue

        param_match = param_pattern.match(stripped_line)
        if param_match:
            param_name = param_match.group(1).strip()
            datatype, description = extract_datatype_description(param_match.group(2).strip())
            additional_description = param_match.group(3).strip() if param_match.group(3) else ""
            if additional_description:
                description += f' {additional_description}'

            parameters.append({
                "name": param_name,
                "datatype": datatype,
                "description": description
            })
        else:
            print("Skipping unmatched parameter line:", stripped_line)  # Debugging remaining issues

    return parameters


def extract_function_details(function_lines):
    """Extract the function name and parameters from the function lines."""
    function_name = None
    input_parameters = []

    for i, line in enumerate(function_lines):
        # Find the function name
        if line.strip().startswith("def "):
            match = re.match(r'def (\w+)\(', line.strip())
            if match:
                function_name = match.group(1)

            # Extract parameters (either inline or across lines)
            params_start = line.find('(')
            params_end = line.find(')')
            if params_start != -1 and params_end != -1:
                param_line = line[params_start + 1:params_end]
                input_parameters = extract_parameters(param_line, function_lines[i + 1:])
            else:
                input_parameters = extract_parameters("", function_lines[i + 1:])

            break

    return function_name, input_parameters


def process_function(function_code, function_id):
    """Process each function's code and extract relevant details."""
    function_lines = function_code.split('\n')
    function_dict = {"id": function_id}

    # Extract function details
    function_name, input_parameters = extract_function_details(function_lines)
    function_dict["FunctionName"] = function_name
    function_dict["InputParameters"] = input_parameters

    # Extract return value and description
    return_value, return_description = extract_return_value(function_lines)
    function_dict["Return"] = return_value if return_value else ""
    function_dict["ReturnDescription"] = return_description if return_description else ""

    # Extract description
    description = extract_description(function_lines)
    function_dict["description"] = description

    # Extract additional key-value pairs (Python, VectorScript, Category)
    for line in function_lines:
        key, value = extract_key_value(line)
        if key and key not in function_dict:
            function_dict[key] = value

    return function_dict
class FunctionExtractor:
    def __init__(self, file_name):
        self.file_name = file_name
        self.functions_data = []

    def read_file(self):
        """Read the contents of the file."""
        with open(self.file_name, 'r') as file:
            return file.read()

    def extract_functions(self):
        """Main function to extract all functions from the file."""
        file_content = self.read_file()
        split_functions = file_content.strip().split(keyword_split_function)
        split_functions = [f"def {func}" if i > 0 else func for i, func in enumerate(split_functions)]

        for i, func_code in enumerate(split_functions):
            func_data = process_function(func_code, i + 1)
            print('func_data: ', i, func_data)
            self.functions_data.append(func_data)

    def save_to_json(self, output_file):
        """Save the extracted functions data to a JSON file."""
        with open(output_file, 'w') as json_file:
            json.dump(self.functions_data, json_file, indent=4)

    def run(self, output_file):
        """Run the entire process from extraction to saving as JSON."""
        self.extract_functions()
        self.save_to_json(output_file)
        print(f'Saved all functions with key-value pairs and description to {output_file}')

# Callable function for external use
def run_extraction(input_file, output_file):
    extractor = FunctionExtractor(input_file)
    extractor.run(output_file)


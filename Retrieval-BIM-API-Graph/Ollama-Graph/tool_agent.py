from tools.llm import llm
from tools.graph import graph
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.schema import StrOutputParser
from langchain.tools import Tool
from langchain_neo4j import Neo4jChatMessageHistory
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain import hub
from utils import get_session_id
from uses import run_uses

from vector import find_chunk
from cypher import run_cypher
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

############################################
# Structured Tools Definition
############################################

class ExplainMeInput(BaseModel):
    query: str = Field(..., description="The query text to find related functions or chunks")

explain_me_tool = StructuredTool.from_function(
    name="Semantic Search",
    description="Use embeddings and vector index to find other potentially related functions. Given a query string, return relevant details.",
    func=find_chunk,
    args_schema=ExplainMeInput,
    response_format="content"
)

class ListAllInput(BaseModel):
    query: str = Field(..., description="query text or conditions to find specific nodes/relations in the graph")

list_all_tool = StructuredTool.from_function(
    name="Graph Query",
    description="Search for special nodes and relations in the graph using the provided keywords. Result: List with nodes in the graph use the result to provide an answer.",
    func=run_cypher,
    args_schema=ListAllInput,

    response_format = "content"
)

class WhatWhichInput(BaseModel):
    query: str = Field(..., description="Find functions related to the output of the General Graph Query and Semantic Search")

what_which_tool = StructuredTool.from_function(
    name="Connected Example Query",
    description="Query connections based on [USES] relationships to find functions related to earlier results.",
    func=run_uses,
    args_schema=WhatWhichInput
)

tools = [explain_me_tool, list_all_tool, what_which_tool]
tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])

def get_memory(session_id):
    return Neo4jChatMessageHistory(session_id=session_id, graph=graph)


agent_prompt = PromptTemplate.from_template("""
## General Instructions
You are a helpful assistant specialized in aiding Vectorworks developers. Your primary goal is to provide accurate, helpful answers. To do this, you will:
- Use the available tools to gather comprehensive and accurate information.
- Combine information from multiple tools if necessary.
- Present the final answer to the user in a clear, concise, and logical manner.

## Tool-Usage Guidelines
Use the tools listed below as needed to find functions, parameters, data types, or other requested information. Follow this sequence when using tools:
1. **Semantic Search**: Use embeddings and a vector index to find relevant functions, parameters, and data types.
2. **General Graph Query**: Given the input, query the graph database for special nodes and relationships.
3. **Connected Example Query**: Use this after the other queries to find functions related to the previously obtained results. This leverages [USES] relationships.

------

### Tools

You have access to the following tools:
{tools}

### How to Use Tools
If you need to call a tool, you MUST use the following format:

```
Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
```
When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:

```
Thought: Do I need to use a tool? No
Final Answer: [Your final answer here]
```

## Answering Guidelines
Follow these case-specific guidelines:

- **List all/Find all:**
  Use the **Graph Query** tool to find categories, parameters, etc..
  Return the results as bullet-pointed lists or as clear, full sentences.

- **Explain me:**
  Use **Semantic Search** tool to gather definitions, usage details. 
  Use the function_names from Semantic Search for **Graph Query** tool input.
  Provide clear, full-sentence explanations.
  You must provide a code implementation in Python using the python property.

- **What/How:**
  Use the **Semantic Search** tools to determine input parameters or return data types.
  Use the function_names from Semantic Search for **Graph Query** tool input.
  Provide clear, full-sentence explanations and code implementation in Python.
  If related functions can be found, use the **Connected Example Query** to list them under "Other Helpful Functions".

## Code Implementation Guideline
When providing code samples, import Vectorworks packages from `vs`.
Use the node property "python" of the function node to find the correct Python invocation for the Vectorworks function.

**Example:**
```python
[your Python code here]
```
------

Begin!

Previous conversation history:
{chat_history}

New input: {input}
{agent_scratchpad}
""")

agent = create_react_agent(llm, tools, agent_prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    handle_parsing_errors=True,
    verbose=True
)

chat_agent = RunnableWithMessageHistory(
    agent_executor,
    get_memory,
    input_messages_key="input",
    history_messages_key="chat_history",
)


def generate_response(user_input):
    """
    Generate a response to the user's input by invoking the agent.

    Args:
        user_input (str): The query or command from the user.

    Returns:
        str: The agent's response based on the tools and logic provided.
    """
    try:
        response = chat_agent.invoke(
            {"input": user_input},
            {"configurable": {"session_id": get_session_id()}},
        )
        return response['output']
    except Exception as e:
        return f"An error occurred: {str(e)}"

import os
from dotenv import load_dotenv
load_dotenv()
import re
import json

from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

from langchain_community.vectorstores import Neo4jVector
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate

from tools.llm import llm, embedding_provider
from tools.graph import graph



instructions = (
    "Use the given context to answer the question."
    "Reply with an answer that includes the id of the document and other relevant information from the text."
    "If you don't know the answer, say you don't know."
    "Context: {context}"
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", instructions),
        ("human", "{input}"),
    ]
)


def create_chunk_vector(user_input):
    """
    Create a Neo4jVector retriever with a query containing user input.
    """
    retrieval_query = f"""
    RETURN node {{.text}} AS text, score, {{documentId: "id", vectorScore: score}} AS metadata
    """
    retrieval_example = Neo4jVector.from_existing_index(
        embedding_provider,
        graph=graph,
        index_name="vectorIndex",
        embedding_node_property="textEmbedding",
        text_node_property=["text"],
        retrieval_query=retrieval_query
    )
    query_result = retrieval_example.similarity_search(user_input, k=3)
    # print(query_result)
    return query_result

def extract_function_names(result):
    """
    Extract function names from the page content of each document in the result.
    """
    function_names = []
    for doc in result:
        # Extract page_content
        page_content = doc.page_content

        # Use regex to find the word after "text:"
        matches = re.findall(r"text:\s*(\w+)", page_content)
        # print(matches)
        function_names.extend(matches)  # Append matches to the list


    return function_names

def extract_full_content(result):
    """
    Extract full text content from the page content of each document in the result.
    """
    full_texts = []
    for doc in result:
        # Extract the full page_content
        page_content = doc.page_content

        # Append the entire page_content to the list
        full_texts.append(page_content)

    return full_texts

def find_chunk(q):
    print("start find_chunk", q)

    result =create_chunk_vector(q)
    # print(result)


    # Extract function names from the result
    function_names = extract_function_names(result)
    function_names_str = ", ".join(function_names)
    # Extract full text content from the result
    full_texts = extract_full_content(result)
    full_texts_str = "\n\n".join(full_texts)  # Join multiple documents with spacing
    # print(full_texts_str)
    return result

# a = find_chunk("What input Parameters has the Function AddHole?")
# print(a)
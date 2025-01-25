import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
# Load environment variables from a .env file
load_dotenv()

#llm with Ollama
llm = ChatOllama(
    model= "llama3.2:latest",
    temperature=0,
    )
# Create the Embedding model with ollama
embedding_provider = OllamaEmbeddings(
    model="mxbai-embed-large"
    )

#llm with GPT
# llmGPT = ChatOpenAI(
#     openai_api_key=os.getenv('OPENAI_API_KEY'),
#     model_name="gpt-4o-mini"
# )
# embedding_provider_gpt = OpenAIEmbeddings(
#     openai_api_key=os.getenv('OPENAI_API_KEY'),
#     model="text-embedding-3-small"
#     )
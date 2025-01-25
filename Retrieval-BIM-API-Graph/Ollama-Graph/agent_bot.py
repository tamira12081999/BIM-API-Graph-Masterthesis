import streamlit as st

# Ensure this is the first Streamlit function called
st.set_page_config("Ebert", page_icon="🎙️")
from utils import write_message
import tool_agent
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant",
         "content": "Hi, I'm your API-Documentation Chatbot! How can I help you?"
         },
    ]

# Submit handler
def handle_submit(message):
    """
    Submit handler:
    You will modify this method to talk with an LLM and provide
    context using data from Neo4j.
    """

    # Handle the response
    with st.spinner('Thinking...'):
        # Call the agent
        response = tool_agent.generate_response(message)
        write_message('assistant', response)

# Display messages in Session State
for message in st.session_state.messages:
    write_message(message['role'], message['content'], save=False)

# Handle any user input
if prompt := st.chat_input("How can I help you?"):
    # Display user message in chat message container
    write_message('user', prompt)

    # Generate a response
    handle_submit(prompt)

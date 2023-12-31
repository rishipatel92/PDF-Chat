import streamlit as st
from dotenv import load_dotenv
import pickle
import os
from streamlit_extras.add_vertical_space import add_vertical_space
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.llms import OpenAI
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

def create_new_chat_session():
    # Function to create a new chat session and set it as active
    chat_id = len(st.session_state.chat_sessions) + 1
    session_key = f"Chat {chat_id}"
    st.session_state.chat_sessions[session_key] = []
    st.session_state.active_session = session_key

def initialize_chat_ui():
    if "active_session" in st.session_state:
        for message in st.session_state.chat_sessions[st.session_state.active_session]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    return st.chat_input("Ask your questions from PDF ")

def main():
    st.sidebar.title('LLM Chat App with Web_Link - Chat History and New Chat Button')
    add_vertical_space(1)
    st.sidebar.write('Made by Rishi Patel for PearlThoughts')
    add_vertical_space(2)

    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = {}

    if "active_session" not in st.session_state:
        create_new_chat_session()

    # New Chat button
    if st.sidebar.button("New Chat"):
        create_new_chat_session()

    # Buttons for previous chat sessions
    for session in st.session_state.chat_sessions:
        if st.sidebar.button(session, key=session):  # Added a unique key
            st.session_state.active_session = session

    st.header("Search for Info from the Link")

    # Enter Your Link
    link = st.text_input("Enter Your Link")
    if link:
        parsed_link = urlparse(link)
        response = requests.get(link)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text_content = soup.get_text()

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len
            )
            chunks = text_splitter.split_text(text=text_content)

            # Use parsed link to get a suitable store name
            store_name = os.path.basename(parsed_link.path)

            if os.path.exists(f"{store_name}.pkl"):
                with open(f"{store_name}.pkl", "rb") as f:
                    vectorstore = pickle.load(f)
            else:
                embeddings = OpenAIEmbeddings()
                vectorstore = FAISS.from_texts(chunks, embedding=embeddings)
                with open(f"{store_name}.pkl", "wb") as f:
                    pickle.dump(vectorstore, f)

            # Chat UI and processing
            llm = OpenAI(temperature=0, max_tokens=1000)
            qa = ConversationalRetrievalChain.from_llm(llm, vectorstore.as_retriever())
            prompt = initialize_chat_ui()

            if prompt:
                st.session_state.chat_sessions[st.session_state.active_session].append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                result = qa({"question": prompt, "chat_history": [(message["role"], message["content"]) for message in
                                                                  st.session_state.chat_sessions[
                                                                      st.session_state.active_session]]})
                full_response = result["answer"]

                with st.chat_message("assistant"):
                    st.markdown(full_response)
                st.session_state.chat_sessions[st.session_state.active_session].append(
                    {"role": "assistant", "content": full_response})

if __name__ == '__main__':
    main()

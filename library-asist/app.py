import logging
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
logging.getLogger("llama_index").setLevel(logging.WARNING)

import os
import asyncio
import streamlit as st
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext, load_index_from_storage
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.readers.base import BaseReader
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.readers.file import PyMuPDFReader
from llama_index.llms.groq import Groq

PERSIST_DIR = "./storage"


@st.cache_resource
def load_agent():
    """Build (or load) the index and agent once, then reuse across all user interactions."""
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

    api_key_val = os.environ.get("groq_api")
    if not api_key_val:
        raise ValueError("GROQ_API_KEY not found. Check the secret name in Lightning AI settings.")

    Settings.llm = Groq(
        api_key=api_key_val,
        model="openai/gpt-oss-120b",
        request_timeout=360.0,
        context_window=8000,
    )

    Settings.text_splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)

    if os.path.exists(os.path.join(PERSIST_DIR, "docstore.json")):
        storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
        index = load_index_from_storage(storage_context)
    else:
        file_extractor: dict[str, BaseReader] = {".pdf": PyMuPDFReader()}
        documents = SimpleDirectoryReader("data", file_extractor=file_extractor).load_data()
        index = VectorStoreIndex.from_documents(documents)
        index.storage_context.persist(persist_dir=PERSIST_DIR)

    query_engine = index.as_query_engine(similarity_top_k=5)

    async def search_documents(query: str) -> str:
        """Useful for answering questions about library policies, procedures,
        city meeting content, and related documents."""
        response = await query_engine.aquery(query)
        return str(response)

    agent = AgentWorkflow.from_tools_or_functions(
        [search_documents],
        llm=Settings.llm,
        system_prompt="""You are a friendly policy assistant for North Liberty
        Library, helping staff and the public understand library policies and
        city meeting content.

        Always use the search_documents tool to find relevant information before
        answering. Base your answers only on what the tool returns — never use
        outside general knowledge.

        Explain things in plain, everyday language. Avoid tables or dense
        formatting unless specifically asked. Lead with the practical bottom
        line, then add detail if needed.

        If the search_documents tool doesn't return relevant information, say
        plainly: "I couldn't find anything on that in our documents" — don't
        guess or fill gaps with outside knowledge.""",
    )
    return agent


agent = load_agent()

st.title("Library & City Info Assistant")
st.write("Ask about library policies, city meetings, and more.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = asyncio.run(agent.run(prompt))
        st.markdown(str(response))

    st.session_state.messages.append({"role": "assistant", "content": str(response)})
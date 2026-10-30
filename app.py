import logging
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
logging.getLogger("llama_index").setLevel(logging.WARNING)

import os
import asyncio
import threading
import streamlit as st
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext, load_index_from_storage
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.readers.base import BaseReader
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.readers.file import PyMuPDFReader
from llama_index.llms.groq import Groq
from llama_index.llms.openrouter import OpenRouter

PERSIST_DIR = "./storage"


def get_secret(name: str):
    """Read a value from Streamlit secrets, falling back to an environment variable."""
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    return value or os.environ.get(name)


# Fully open model (open weights, training data, and code) from Ai2, served via OpenRouter.
OPEN_MODEL = "allenai/olmo-3.1-32b-instruct"


def pick_llm():
    """Return (label, llm). Uses the fully open OLMo model if an OpenRouter key is set; otherwise Groq."""
    openrouter_key = get_secret("openrouter_api")
    if openrouter_key:
        model = get_secret("llm_model") or OPEN_MODEL
        label = f"{model} (via OpenRouter)"
        return label, OpenRouter(
            api_key=openrouter_key,
            model=model,
            is_function_calling_model=True,
            context_window=65536,
            max_tokens=2048,
            timeout=360.0,
        )

    groq_key = get_secret("groq_api")
    if not groq_key:
        raise ValueError("No model key found. Add openrouter_api or groq_api in Streamlit Cloud: App settings → Secrets.")
    return "openai/gpt-oss-120b (via Groq)", Groq(
        api_key=groq_key,
        model="openai/gpt-oss-120b",
        request_timeout=360.0,
        context_window=8000,
    )

#code to make references easier to read from file names
def friendly_source(metadata: dict) -> str:
    """Turn a chunk's file info into a readable source label."""
    name = metadata.get("file_name", "Unknown document")
    if name.startswith("video_"):
        video_id = name[6:17]  # YouTube IDs are always 11 characters
        title = name[18:].removesuffix(".txt")
        return f"{title} (video: https://youtu.be/{video_id})"
    if name.endswith(".pdf"):
        page = metadata.get("source")  # the PDF reader stores the page number here
        return f"{name.removesuffix('.pdf')}, page {page}" if page else name
    return name
    
@st.cache_resource
def load_agent():
    """Build (or load) the index and agent once, then reuse across all user interactions."""
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

    model_label, Settings.llm = pick_llm()

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
        sources = []
        for item in response.source_nodes:
            label = friendly_source(item.node.metadata)
            if label not in sources:  # skip repeats when several chunks come from one file
                sources.append(label)
        source_list = "\n".join(f"- {s}" for s in sources)
        return f"{response}\n\nSources:\n{source_list}"

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
        guess or fill gaps with outside knowledge.
        
        End every answer with the "Sources:" list from the search results,
        copied exactly. Never add a source the tool didn't return.""",
    )
    return agent, model_label


agent, model_label = load_agent()

@st.cache_resource
def get_event_loop():
    """One long-running event loop on a background thread, shared by all users.
    The LlamaIndex agent must run inside a live loop, and reusing one loop keeps
    its connections to Groq working from question to question."""
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    return loop


def ask_agent(question: str) -> str:
    async def _run():
        return await agent.run(question)
    future = asyncio.run_coroutine_threadsafe(_run(), get_event_loop())
    return str(future.result(timeout=300))



st.title("Library & City Info Assistant")
st.write("Ask about library policies, city meetings, and more.")
st.caption(f"Model: {model_label}")

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
            response = ask_agent(prompt)
        st.markdown(str(response))

    st.session_state.messages.append({"role": "assistant", "content": str(response)})

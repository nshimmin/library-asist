import logging
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
logging.getLogger("llama_index").setLevel(logging.WARNING)

import os
import json
import asyncio
import threading
import streamlit as st
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from llama_index.core.llms import ChatMessage
from llama_index.core import Settings, StorageContext, load_index_from_storage
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from search import EMBED_MODEL, HybridSearch   # shared search settings (see search.py)
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

GAP_PHRASE = "couldn't find anything"

def log_gap(question: str) -> None:
    """Add an unanswered question to the GitHub Issue. Logs only the question and time."""
    token = get_secret("github_token")
    issue = get_secret("gap_issue_number")
    if not token or not issue:
        return  # gap log not set up, so skip quietly
    when = datetime.now(ZoneInfo("America/Chicago")).strftime("%b %-d, %Y, %-I:%M %p")
    try:
        requests.post(
            f"https://api.github.com/repos/nshimmin/library-asist/issues/{issue}/comments",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"body": f"**{when}**\n> {question}"},
            timeout=10,
        )
    except Exception:
        pass  # never let the log break the chat

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

# Titles and web addresses recorded by the import scripts - see webimport.py
try: 
    with open("sources.json", encoding="utf-8") as f:
        SOURCE_INFO = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    SOURCE_INFO = {} # no catalog, so fall back to file names. 

#code to make references easier to read from file names
def friendly_source(metadata: dict) -> str:
    """Turn a chunk's file info into a readable source label."""
    name = metadata.get("file_name", "Unknown document")
    info = SOURCE_INFO.get(name)
    if info: 
        return f"{info['title']} ({info['url']})"
    if name.startswith("video_"):
        video_id = name[6:17]  # YouTube IDs are always 11 characters
        title = name[18:].removesuffix(".txt")
        return f"{title} (video: https://youtu.be/{video_id})"
    if name.endswith(".pdf"):
        page = metadata.get("source")  # the PDF reader stores the page number here
        return f"{name.removesuffix('.pdf')}, page {page}" if page else name
    return name.rsplit(".", 1)[0]
    
@st.cache_resource
def load_agent():
    """Build (or load) the index and agent once, then reuse across all user interactions."""
    Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)

    model_label, Settings.llm = pick_llm()

    # The index is built ahead of time by build_index.py (in Codespaces) and committed.
    if not os.path.exists(os.path.join(PERSIST_DIR, "docstore.json")):
        raise FileNotFoundError("No search index found. Run build_index.py and push the storage folder.")
    index = load_index_from_storage(StorageContext.from_defaults(persist_dir=PERSIST_DIR))
    searcher = HybridSearch(index)   # meaning + keyword search, then reranker

    async def search_documents(query: str) -> str:
        """Search the library's and city's documents (policies, services, web
        pages, the staff FAQ, board information, and city meeting records).
        Returns numbered passages, each labeled with its source."""
        # The reranker takes a few seconds; run it off the main loop so other users aren't blocked
        passages = await asyncio.to_thread(searcher.search, query)
        if not passages:
            return "No relevant passages found."
        blocks = []
        for i, n in enumerate(passages, 1):
            source = friendly_source(n.node.metadata)
            blocks.append(f"[{i}] Source: {source}\n{n.node.get_content().strip()}")
        return "\n\n---\n\n".join(blocks)

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

        If the search_documents tool doesn't return relevant information, start your answer with exactly: 
        "I couldn't find anything about [topic] in our documents."  Then suggest asking
        library staff.  Do not say or imply the library
        doesn't offer it, and don't draw conclusions from what a list of
        services leaves out. Only say "no" when a document clearly says no.
        This rule comes before "lead with the bottom line."

        Example:
        Question: Can I rent a telescope?
        Answer: I couldn't find anything about telescope rentals in our
        documents. Library staff can tell you whether it's available.

        Don't guess or fill gaps with outside knowledge.
        
        For questions about dates ("next", "upcoming"), use today's date (given in a separate note).  Provide 
        distinct notation that an event has passed if it has already passed.
        
        The search tool returns numbered passages, each with its source. Use only
        the passages that actually answer the question and ignore the rest.
        End every answer with "Sources:" followed by the source of each passage
        you used, one per line starting with "- ", copied exactly as given.
        Never list a source you didn't use or the tool didn't return. If no
        passage answers the question, follow the "couldn't find" rule above
        and list no sources.""",
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
    today = datetime.now(ZoneInfo("America/Chicago")).strftime("%A, %B %-d, %Y")
    date_note = ChatMessage(role="system", content=f"Today is {today}.")
    
    async def _run():
        return await agent.run(user_msg=question, chat_history=[date_note])
    future = asyncio.run_coroutine_threadsafe(_run(), get_event_loop())
    return str(future.result(timeout=300))



st.title("MordecAI v0.1: Library & City Info Assistant")
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
        answer = str(response).replace("$", "\\$")
        if GAP_PHRASE in answer.replace("’", "'").lower():
            log_gap(prompt)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

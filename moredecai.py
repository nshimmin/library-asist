from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext, load_index_from_storage
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.file import PyMuPDFReader
from llama_index.core.readers.base import BaseReader
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.groq import Groq
import asyncio
import os
import logging

logging.basicConfig(level=logging.WARNING)  # sets a sane default for everything
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
logging.getLogger("llama_index").setLevel(logging.WARNING)

Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5"
)

api_key_val = os.environ.get("groq_api")
if not api_key_val:
    raise ValueError(
        "GROQ_API_KEY not found. Set it as an environment variable in your Lightning AI Studio settings."
    )

Settings.llm = Groq(
    api_key=api_key_val,
    model="openai/gpt-oss-120b",
    request_timeout=360.0,
    context_window=8000,
)

Settings.text_splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)

PERSIST_DIR = "./storage"

if os.path.exists(os.path.join(PERSIST_DIR, "docstore.json")):
    storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
    index = load_index_from_storage(storage_context)
    print("Loaded existing index from disk.")
else:
    file_extractor: dict[str, BaseReader] = {".pdf": PyMuPDFReader(),}
    documents = SimpleDirectoryReader(
        "data",
        file_extractor=file_extractor,
    ).load_data()

    index = VectorStoreIndex.from_documents(documents)
    index.storage_context.persist(persist_dir=PERSIST_DIR)
    print("Built new index and saved to disk.")

query_engine = index.as_query_engine(similarity_top_k=5)


async def search_documents(query: str) -> str:
    """Useful for answering questions about library policies and procedures,
    including rules, staff guidelines, and operational details found in the
    library policy manual (e.g., proctoring, meeting room use, conduct policies)."""
    response = await query_engine.aquery(query)
    return str(response)


agent = AgentWorkflow.from_tools_or_functions(
    [search_documents],
    llm=Settings.llm,
    system_prompt="""You are a friendly policy assistant for the North Liberty Library in North Liberty Iowa, helping
staff and the public understand library policies, procedures, and find information.

Always use the search_documents tool to find relevant policy information before
answering. Base your answers only on what the tool returns — never use outside
general knowledge about libraries or policies in general.

Once you have the relevant policy text:
- Explain it in plain, everyday language, like you're talking to a neighbor,
  not reading from a manual
- Avoid tables, bullet-heavy formatting, or legalistic phrasing unless the
  person specifically asks for a structured breakdown
- Prefer short paragraphs or a simple list over dense multi-column layouts
- Lead with the practical bottom line, then fill in details if needed

If the search_documents tool doesn't return relevant information, say plainly:
"I couldn't find anything on that in the policy manual" — don't guess or fill
gaps with outside knowledge.""",
)


async def main():
    print("Ask me anything (type 'exit' or 'quit' to stop):\n")
    while True:
        question = input("You: ").strip()
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue
        response = await agent.run(question)
        print(f"\nAgent: {response}\n")


if __name__ == "__main__":
    asyncio.run(main())
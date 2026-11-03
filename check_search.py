"""Show what the search finds for each test question, with match scores.
Use it to see where good matches and poor matches fall, then pick a cutoff."""
import sys
from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Must match app.py and build_index.py
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

QUESTIONS = [
    "When is the next library board meeting?",
    "Does the library offer language learning classes?",
    "Who is on the library board?",
    "Can I get something notarized?",
    "Can I fax something at the library?",
    "How much does it cost to print?",
    "Can I rent a telescope?",           # not in the documents
    "Do you offer passport photos?",     # not in the documents
]

index = load_index_from_storage(StorageContext.from_defaults(persist_dir="storage"))
retriever = index.as_retriever(similarity_top_k=8)

for q in (sys.argv[1:] or QUESTIONS):
    print(f"\n=== {q}")
    for n in retriever.retrieve(q):
        name = n.node.metadata.get("file_name", "?")[:60]
        preview = " ".join(n.node.get_content().split())[:70]
        print(f"  {n.score:.3f}  {name}  | {preview}")

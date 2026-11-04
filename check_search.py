"""Show what the search finds for each test question, with match scores.
Use it to see where good matches and poor matches fall, then pick a cutoff.

  python check_search.py                       # plain search (embedding scores)
  python check_search.py "your question"       # test your own question
  python check_search.py --rerank MODEL_NAME   # also re-score with a reranker
"""
import sys
import time
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

# Read options: --rerank MODEL, then any questions typed after it
args = sys.argv[1:]
reranker = None
if "--rerank" in args:
    i = args.index("--rerank")
    model_name = args[i + 1]
    del args[i:i + 2]
    from llama_index.core.postprocessor import SentenceTransformerRerank
    print(f"Loading reranker {model_name} ...")
    reranker = SentenceTransformerRerank(model=model_name, top_n=8)

index = load_index_from_storage(StorageContext.from_defaults(persist_dir="storage"))
# With a reranker, pull more candidates for it to choose from
retriever = index.as_retriever(similarity_top_k=20 if reranker else 8)

for q in (args or QUESTIONS):
    print(f"\n=== {q}")
    start = time.time()
    nodes = retriever.retrieve(q)
    first_rank = {n.node.node_id: rank for rank, n in enumerate(nodes, 1)}
    if reranker:
        nodes = reranker.postprocess_nodes(nodes, query_str=q)
    for n in nodes:
        name = n.node.metadata.get("file_name", "?")[:55]
        preview = " ".join(n.node.get_content().split())[:65]
        was = f"(was #{first_rank[n.node.node_id]:>2})  " if reranker else ""
        print(f"  {n.score:7.3f}  {was}{name}  | {preview}")
    if reranker:
        print(f"  [{time.time() - start:.1f} seconds]")

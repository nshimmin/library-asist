"""Show what the search finds for each test question, with match scores.
Use it to see where good matches and poor matches fall, then pick settings.

  python check_search.py                       # meaning search only (embedding scores)
  python check_search.py "your question"       # test your own question
  python check_search.py --hybrid              # meaning + keyword search, combined
  python check_search.py --rerank MODEL_NAME   # re-score results with a reranker
  (options can be combined, e.g. --hybrid --rerank MODEL_NAME)
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
CANDIDATES = 20   # how many results each search hands on
SHOW = 8          # how many to print


def combine(meaning_results, keyword_results):
    """Merge two ranked lists with Reciprocal Rank Fusion: each search "votes"
    1/(60 + rank) for every chunk it found. Chunks near the top of either list,
    or found by both, end up first. Uses ranks, not scores, because the two
    searches score on completely different scales."""
    votes, chunks, found_by = {}, {}, {}
    for label, results in (("M", meaning_results), ("K", keyword_results)):
        for rank, n in enumerate(results, 1):
            cid = n.node.node_id
            votes[cid] = votes.get(cid, 0) + 1 / (60 + rank)
            chunks[cid] = n
            found_by.setdefault(cid, []).append(f"{label}#{rank}")
    order = sorted(votes, key=votes.get, reverse=True)
    for cid in order:
        chunks[cid].score = votes[cid]
    return [chunks[cid] for cid in order], found_by


# Read options
args = sys.argv[1:]
hybrid = "--hybrid" in args
if hybrid:
    args.remove("--hybrid")
reranker = None
if "--rerank" in args:
    i = args.index("--rerank")
    model_name = args[i + 1]
    del args[i:i + 2]
    from llama_index.core.postprocessor import SentenceTransformerRerank
    print(f"Loading reranker {model_name} ...")
    reranker = SentenceTransformerRerank(model=model_name, top_n=SHOW)

index = load_index_from_storage(StorageContext.from_defaults(persist_dir="storage"))
meaning = index.as_retriever(similarity_top_k=CANDIDATES if (hybrid or reranker) else SHOW)
if hybrid:
    from llama_index.retrievers.bm25 import BM25Retriever
    keyword = BM25Retriever.from_defaults(docstore=index.docstore, similarity_top_k=CANDIDATES)

for q in (args or QUESTIONS):
    print(f"\n=== {q}")
    start = time.time()
    found_by = {}
    if hybrid:
        nodes, found_by = combine(meaning.retrieve(q), keyword.retrieve(q))
        nodes = nodes[:CANDIDATES]
    else:
        nodes = meaning.retrieve(q)
    if reranker:
        nodes = reranker.postprocess_nodes(nodes, query_str=q)
    for n in nodes[:SHOW]:
        name = n.node.metadata.get("file_name", "?")[:50]
        preview = " ".join(n.node.get_content().split())[:60]
        tag = f"[{' '.join(found_by[n.node.node_id])}]".ljust(13) if hybrid else ""
        print(f"  {n.score:7.3f}  {tag}{name}  | {preview}")
    if reranker or hybrid:
        print(f"  [{time.time() - start:.1f} seconds]")

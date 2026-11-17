"""Show exactly what the app's search finds for each question, step by step.
Uses the same settings as the app (from search.py), so what you see here is
what the AI model gets. No AI model is called, so it costs nothing.

  python check_search.py                    # run the test questions
  python check_search.py "your question"    # test your own question(s)

Searches the official documents, like the app's main search tool. Add:
  --meetings   to search the meeting transcripts instead (any collection works:
               --<folder name in data/>)
  --all        to search everything together (the old way, for comparison)

Each line shows:  reranker score, which search found it, file, and a preview.
  M#3 = meaning search ranked it 3rd;  K#1 = keyword search ranked it 1st
  ->  = handed to the AI model (above the cutoff and within the top N)
"""
import sys
import time
from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from search import EMBED_MODEL, MIN_SCORE, TOP_N, HybridSearch, collection

Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)

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
SHOW = 10   # how many candidates to print per question

args = sys.argv[1:]
flags = [a[2:] for a in args if a.startswith("--")]
which = flags[0] if flags else "official"   # a collection's folder name
if "all" in flags:
    which = None
questions = [a for a in args if not a.startswith("--")] or QUESTIONS

index = load_index_from_storage(StorageContext.from_defaults(persist_dir="storage"))
searcher = HybridSearch(index, which)
if not searcher.size and which:
    names = sorted({collection(c.metadata) for c in index.docstore.docs.values()})
    sys.exit(f'No collection named "{which}". Collections: {", ".join(names)}')
print(f"Searching: {which or 'everything'} ({searcher.size} chunks)   Cutoff: {MIN_SCORE}   Top N: {TOP_N}")

for q in questions:
    print(f"\n=== {q}")
    start = time.time()
    ranked, found_by = searcher.rank(q)
    sent = 0
    for n in ranked[:SHOW]:
        handed_on = n.score >= MIN_SCORE and sent < TOP_N
        sent += handed_on
        arrow = "->" if handed_on else "  "
        tag = f"[{' '.join(found_by[n.node.node_id])}]".ljust(13)
        name = n.node.metadata.get("file_name", "?")[:45]
        preview = " ".join(n.node.get_content().split())[:55]
        print(f" {arrow} {n.score:7.2f}  {tag}{name}  | {preview}")
    print(f"  [{sent} passage(s) handed to the AI model, {time.time() - start:.1f} seconds]")

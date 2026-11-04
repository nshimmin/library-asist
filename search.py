"""How documents are chunked and searched: one place for all search settings.

build_index.py, app.py, and check_search.py all read their settings from here,
so they can't drift apart. (If the index were built one way and searched
another, search would quietly return poor results.)

The search has three steps:
  1. Meaning search   - finds passages about the same idea, even in different words
  2. Keyword search   - finds passages with the same words (good for terms like "fax")
  3. Reranker         - reads the question with each passage and re-sorts them by
                        how well the passage actually answers the question
Then it keeps only passages that score above a cutoff, up to TOP_N of them.
"""
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter

# ---- Settings ---------------------------------------------------------------
EMBED_MODEL = "BAAI/bge-small-en-v1.5"                 # meaning search model
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # reranker model (~90 MB)
CANDIDATES = 20    # how many passages each search hands on to the reranker
TOP_N = 5          # most passages handed to the AI model (keeps us under Groq's limits)
MIN_SCORE = -7.0   # reranker scores below this mean "not related to the question".
                   # Chosen Nov 4, 2026 with check_search.py: passages that answered
                   # test questions scored -5.1 or higher; results for questions the
                   # documents don't cover scored -8.4 or lower.


def chunkers():
    """How documents are cut into chunks: at headings first, then by size."""
    return [
        MarkdownNodeParser(),                                # 1. cut at headings
        SentenceSplitter(chunk_size=512, chunk_overlap=50),  # 2. cap the size
    ]


def combine(meaning_results, keyword_results):
    """Merge two ranked lists with Reciprocal Rank Fusion: each search "votes"
    1/(60 + rank) for every passage it found. Passages near the top of either
    list, or found by both, come first. Uses ranks, not scores, because the two
    searches score on completely different scales.

    Returns the merged list and, for each passage, which search found it
    (e.g. "M#3 K#1" = meaning search ranked it 3rd, keyword search 1st)."""
    votes, passages, found_by = {}, {}, {}
    for label, results in (("M", meaning_results), ("K", keyword_results)):
        for rank, n in enumerate(results, 1):
            pid = n.node.node_id
            votes[pid] = votes.get(pid, 0) + 1 / (60 + rank)
            passages[pid] = n
            found_by.setdefault(pid, []).append(f"{label}#{rank}")
    order = sorted(votes, key=votes.get, reverse=True)
    for pid in order:
        passages[pid].score = votes[pid]
    return [passages[pid] for pid in order], found_by


class HybridSearch:
    """Meaning search + keyword search, combined, then re-sorted by a reranker."""

    def __init__(self, index):
        from llama_index.core.postprocessor import SentenceTransformerRerank
        from llama_index.retrievers.bm25 import BM25Retriever

        self.meaning = index.as_retriever(similarity_top_k=CANDIDATES)
        self.keyword = BM25Retriever.from_defaults(docstore=index.docstore,
                                                   similarity_top_k=CANDIDATES)
        self.reranker = SentenceTransformerRerank(model=RERANK_MODEL, top_n=CANDIDATES)

    def rank(self, question):
        """Every candidate passage, best first, with reranker scores.
        Also returns which search found each one (used by check_search.py)."""
        merged, found_by = combine(self.meaning.retrieve(question),
                                   self.keyword.retrieve(question))
        ranked = self.reranker.postprocess_nodes(merged[:CANDIDATES], query_str=question)
        return ranked, found_by

    def search(self, question):
        """The passages the app hands to the AI model."""
        ranked, _ = self.rank(question)
        return [n for n in ranked if n.score >= MIN_SCORE][:TOP_N]

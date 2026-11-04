"""Rebuild the search index from everything in data/.
Run this after adding or updating documents, then commit the storage/ folder."""
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SentenceSplitter, MarkdownNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.readers.file import PyMuPDFReader

# These two settings MUST match app.py, or searches won't line up with the index
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.text_splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)

documents = SimpleDirectoryReader("data", file_extractor={".pdf": PyMuPDFReader()}).load_data()
print(f"Loaded {len(documents)} documents")

index = VectorStoreIndex.from_documents(
    documents,
    transformations=[
        MarkdownNodeParser(),                                # 1. cut at headings first
        SentenceSplitter(chunk_size=512, chunk_overlap=50),  # 2. then cap the size
    ],
    show_progress=True,
)
index.storage_context.persist(persist_dir="storage")
print("Saved the new index to storage/")

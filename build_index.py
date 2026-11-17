"""Rebuild the search index from everything in data/.
Run this after adding or updating documents, then commit the storage/ folder."""
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.ingestion import run_transformations
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.readers.file import PyMuPDFReader
from search import EMBED_MODEL, chunkers   # shared settings, so the app always matches
from sources import label_document, label_chunk   # each chunk's source line: title and department

Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)

documents = SimpleDirectoryReader("data", file_extractor={".pdf": PyMuPDFReader()}).load_data()
print(f"Loaded {len(documents)} documents")
for doc in documents:
    label_document(doc)   # e.g. "title: Room Reservations / department: Library"

chunks = run_transformations(documents, chunkers(), show_progress=True)   # cut at headings, then by size
for chunk in chunks:
    label_chunk(chunk)    # a section about one board gets that board as its department
print(f"Cut into {len(chunks)} chunks")

index = VectorStoreIndex(chunks, show_progress=True)
index.storage_context.persist(persist_dir="storage")
print("Saved the new index to storage/")

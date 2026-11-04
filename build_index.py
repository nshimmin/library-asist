"""Rebuild the search index from everything in data/.
Run this after adding or updating documents, then commit the storage/ folder."""
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.readers.file import PyMuPDFReader
from search import EMBED_MODEL, chunkers   # shared settings, so the app always matches

Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)

documents = SimpleDirectoryReader("data", file_extractor={".pdf": PyMuPDFReader()}).load_data()
print(f"Loaded {len(documents)} documents")

index = VectorStoreIndex.from_documents(documents, transformations=chunkers(), show_progress=True)
index.storage_context.persist(persist_dir="storage")
print("Saved the new index to storage/")

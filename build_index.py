"""Build the search index from data/, processing only what changed.

Each folder in data/ is one collection, searched on its own (data/official/,
data/meetings/). See search.py.

The build keeps a fingerprint of every document in storage/build_manifest.json.
Each time it runs, it compares the documents with those fingerprints:
  - new or changed documents are read, cut into chunks, and embedded
  - removed documents are taken out of the index
  - unchanged documents are left alone
So a large document costs its build time once, and a small edit takes seconds.

  python build_index.py          # update the index with what changed
  python build_index.py --full   # start over and rebuild everything

Everything is rebuilt on its own when a setting that shapes every chunk
changes (the embedding model, chunk sizes, or department rules).

Run this after adding, changing, moving, or removing documents, then commit
the storage/ folder.
"""
import hashlib
import json
import sys
from pathlib import Path

from llama_index.core import (Settings, SimpleDirectoryReader, StorageContext,
                              VectorStoreIndex, load_index_from_storage)
from llama_index.core.ingestion import run_transformations
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.readers.file import PyMuPDFReader

import search    # shared search settings, so the app always matches
import sources   # each chunk's source line: title and department
from sources import label_chunk, label_document

DATA = Path("data")
STORAGE = Path("storage")
MANIFEST = STORAGE / "build_manifest.json"
BUILD_VERSION = 1   # raise this when a change to this script changes the chunks

# Windows saves line breaks as \r\n, Linux (the Codespace) as \n, and git
# converts between them. Text is read and fingerprinted with plain \n, so a
# document gives the same chunks, and counts as unchanged, on any computer.
TEXT_TYPES = {".txt", ".md", ".csv", ".json", ".html", ".htm"}
# File details the reader adds that differ from one computer (or git
# checkout) to the next. They'd only clutter the saved index.
DROPPED_DETAILS = ("creation_date", "last_modified_date", "last_accessed_date", "file_size")


def fingerprint(data):
    """A short code that changes whenever the data changes at all."""
    return hashlib.sha256(data).hexdigest()


def settings_fingerprint():
    """One fingerprint for the settings that shape every chunk. If it changes,
    every chunk would come out differently, so everything is rebuilt."""
    settings = {
        "build": BUILD_VERSION,
        "embed_model": search.EMBED_MODEL,
        "chunk_size": search.CHUNK_SIZE,
        "chunk_overlap": search.CHUNK_OVERLAP,
        "departments": [sources.DEPARTMENT_BY_WEBSITE, sources.DEPARTMENT_BY_TITLE,
                        sources.DEFAULT_DEPARTMENT],
        "searched_fields": sources.SEARCHED_FIELDS,
    }
    return fingerprint(json.dumps(settings, sort_keys=True).encode())


def find_documents():
    """Every document in data/, by its place in data/ (e.g. "official/web_0.txt")."""
    found = {}
    for path in sorted(DATA.rglob("*")):
        place = path.relative_to(DATA)
        if path.is_file() and not any(part.startswith(".") for part in place.parts):
            found[place.as_posix()] = path   # forward slashes on every computer
    return found


def collection_of(place):
    """The collection is the first folder: "meetings/video_x.txt" -> "meetings"."""
    folders = place.split("/")[:-1]
    return folders[0] if folders else search.DEFAULT_COLLECTION


def describe(place, path):
    """What the build remembers about a document. If any of it changes
    (the file itself, its folder, or its title or department in
    sources.json), the document is processed again."""
    content = path.read_bytes()
    if path.suffix.lower() in TEXT_TYPES:
        content = content.replace(b"\r\n", b"\n")
    catalog = {"file_name": path.name}
    return {
        "fingerprint": fingerprint(content),
        "collection": collection_of(place),
        "title": sources.source_title(catalog),
        "department": sources.department(catalog),
    }


def read_document(place, path):
    """Read one file (a PDF gives one document per page) and label it."""
    docs = SimpleDirectoryReader(input_files=[path],
                                 file_extractor={".pdf": PyMuPDFReader()}).load_data()
    for i, doc in enumerate(docs):
        # The same ID on every computer, so this file's chunks can be found
        # and replaced the next time it changes
        doc.id_ = f"{place}#{i}"
        doc.set_content(doc.get_content().replace("\r\n", "\n"))
        for key in DROPPED_DETAILS:
            doc.metadata.pop(key, None)
        doc.metadata["file_path"] = f"data/{place}"   # not the full path on this computer
        doc.metadata["collection"] = collection_of(place)
        label_document(doc)   # e.g. "title: Room Reservations / department: Library"
    return docs


def load_manifest():
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def main():
    full = "--full" in sys.argv[1:]
    settings = settings_fingerprint()
    manifest = load_manifest()
    if full:
        print("Rebuilding everything (--full).")
    elif not manifest or not (STORAGE / "docstore.json").exists():
        print("No record of an earlier build, so everything will be built.")
        full = True
    elif manifest.get("settings") != settings:
        print("A setting that shapes every chunk changed (embedding model, chunk "
              "sizes, or department rules), so everything will be rebuilt.")
        full = True
    before = {} if full else manifest["documents"]

    # ---- Compare the documents with the last build ---------------------------
    now = {place: describe(place, path) for place, path in find_documents().items()}
    added = [p for p in now if p not in before]
    removed = [p for p in before if p not in now]
    changed = [p for p in now if p in before
               and any(before[p].get(k) != v for k, v in now[p].items())]
    unchanged = len(now) - len(added) - len(changed)
    if full:
        print(f"{len(now)} documents to build")
    else:
        for label, places in (("New", added), ("Changed", changed), ("Removed", removed)):
            for place in places:
                print(f"  {label}: {place}")
        print(f"{len(added)} new, {len(changed)} changed, {len(removed)} removed, "
              f"{unchanged} unchanged")
    if not (full or added or changed or removed):
        print("Nothing to do: the index is up to date.")
        return

    # ---- Update the index ----------------------------------------------------
    Settings.embed_model = HuggingFaceEmbedding(model_name=search.EMBED_MODEL)
    if full:
        index = VectorStoreIndex([], show_progress=True)   # start empty
    else:
        index = load_index_from_storage(StorageContext.from_defaults(persist_dir=STORAGE),
                                        show_progress=True)
        for place in changed + removed:   # take out the old chunks
            for doc_id in before[place]["doc_ids"]:
                index.delete_ref_doc(doc_id, delete_from_docstore=True)

    to_read = added + changed
    documents = {place: read_document(place, DATA / place) for place in to_read}
    chunks = run_transformations([d for docs in documents.values() for d in docs],
                                 search.chunkers(), show_progress=True)   # cut at headings, then by size
    for chunk in chunks:
        label_chunk(chunk)    # a section about one board gets that board as its department
    print(f"Cut {len(to_read)} documents into {len(chunks)} chunks")
    index.insert_nodes(chunks)   # embeds the new chunks and adds them
    index.storage_context.persist(persist_dir=STORAGE)

    # ---- Remember what was built ---------------------------------------------
    chunk_counts = {}
    for chunk in chunks:
        place = chunk.ref_doc_id.rsplit("#", 1)[0]
        chunk_counts[place] = chunk_counts.get(place, 0) + 1
    record = {}
    for place, info in now.items():
        if place in documents:
            record[place] = {**info, "doc_ids": [d.id_ for d in documents[place]],
                             "chunks": chunk_counts.get(place, 0)}
        else:
            record[place] = before[place]
    MANIFEST.write_text(json.dumps({"settings": settings, "documents": record},
                                   indent=1, ensure_ascii=False), encoding="utf-8")

    totals = {}
    for info in record.values():
        name = info["collection"]
        docs, count = totals.get(name, (0, 0))
        totals[name] = (docs + 1, count + info["chunks"])
    print("Saved the index to storage/. Collections:")
    for name, (docs, count) in sorted(totals.items()):
        print(f"  {name}: {docs} documents, {count} chunks")


if __name__ == "__main__":
    main()

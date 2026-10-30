from pathlib import Path
from llama_index.readers.web import SimpleWebPageReader

urls = [
    "https://northlibertylibrary.org/about/accessibility/",
    "https://northlibertylibrary.org/program/adventure-pass/",
    "https://northlibertylibrary.org/program/book-bike/",
    "https://northlibertylibrary.org/program/storywalk/",
    "https://northlibertylibrary.org/program/reading-challenges/",
    "https://northlibertylibrary.org/program/seeds-plants-and-gardening/",
    "https://northlibertylibrary.org/resources/",
    "https://northlibertylibrary.org/resources/room-reservations/",
]

Path("data").mkdir(exist_ok=True)

documents = SimpleWebPageReader(html_to_text=True).load_data(urls=urls)

for i, doc in enumerate(documents):
    filepath = Path("data") / f"web_{i}.txt"
    filepath.write_text(doc.text, encoding="utf-8")
    print(f"Saved {filepath}")
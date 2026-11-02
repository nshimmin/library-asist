import json
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
    "https://northliberty-ia.whofi.com/",
    "https://northlibertyiowa.gov/board-commissions/",
]

Path("data").mkdir(exist_ok=True)

# The "card catalog": file name -> title and web address.
# Load the existing one (if any) so other import scripts can add to it too.
sources_file = Path("sources.json")
sources = json.loads(sources_file.read_text()) if sources_file.exists() else {}

documents = SimpleWebPageReader(html_to_text=True).load_data(urls=urls)

for i, (url, doc) in enumerate(zip(urls, documents)):
    filename = f"web_{i}.txt" 
    (Path("data") / filename).write_text(doc.text, encoding="utf-8")
    # Use the page's first heading ("# Book Bike") as its title; fall back to the URL
    title = next((line[2:].strip() for line in doc.text.splitlines() if line.startswith("# ")), url)
    sources[filename] = {"title": title, "url": url}
    print(f"Saved {filename}: {title}")

sources_file.write_text(json.dumps(sources, indent=2), encoding="utf-8")
print(f"Updated {sources_file}")

import json
from pathlib import Path
import trafilatura
import html2text

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

WHOLE_PAGE_URLS = {
    "https://northliberty-ia.whofi.com/",
}

Path("data").mkdir(exist_ok=True)

# The "card catalog": file name -> title and web address.
# Load the existing one (if any) so other import scripts can add to it too.
sources_file = Path("sources.json")
sources = json.loads(sources_file.read_text()) if sources_file.exists() else {}

for i, url in enumerate(urls):
    filename = f"web_{i}.txt" 

    html = trafilatura.fetch_url(url)
    if html is None: 
        print(f"Couldn't download {url} - keeping the old copy of {filename}")
        continue
    
    if url in WHOLE_PAGE_URLS:
        text = html2text.html2text(html)      # whole page, links included
    else:
        # trafilatura finds the page's main content and drops menus, footers, and ads.
        # favor_recall=True leans toward keeping text when it isn't sure.
        text = trafilatura.extract(html, output_format="markdown", include_links=False, include_tables=True, favor_recall=True)
    if not text:
        print(f"No main content found on {url} - keeping the old copy of {filename}")
        continue
    
    (Path("data") / filename).write_text(text, encoding="utf-8")
    
    meta = trafilatura.extract_metadata(html)
    title = meta.title if meta and meta.title else url
    sources[filename] = {"title": title, "url": url}
    print(f"Saved {filename}: {title} ({len(text):,} characters)")

sources_file.write_text(json.dumps(sources, indent=2), encoding="utf-8")
print(f"Updated {sources_file}")

"""Where each document comes from: its title, web address, and department.

Used in two places:
  - build_index.py stamps every chunk with a "source line" (title and
    department), so the search knows where a passage comes from even when the
    passage itself doesn't say. Example: the "Reservation Details" section of
    the Room Reservations page now carries "Room Reservations / Library".
  - app.py uses friendly_source() to label passages and answers.

Titles and web addresses come from sources.json (the "card catalog").
Departments come from sources.json if an entry has one, otherwise from the
rules below. Another community would edit these rules for its own departments.
"""
import json
import re

try:
    with open("sources.json", encoding="utf-8") as f:
        SOURCE_INFO = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    SOURCE_INFO = {}   # no catalog, so fall back to file names

# ---- Department rules (edit these for your community) ------------------------
# Web pages: by web address
DEPARTMENT_BY_WEBSITE = [
    ("northlibertylibrary.org", "Library"),
    ("whofi.com", "Library"),              # the library's event calendar
    ("northlibertyiowa.gov", "City of North Liberty"),
    ("northlibertyiowa.org", "City of North Liberty"),
]
# Meeting videos: by words in the title, checked in this order (first match wins)
DEPARTMENT_BY_TITLE = [
    (r"library board", "Library Board of Trustees"),
    (r"mpojc|metropolitan planning", "Metropolitan Planning Organization of Johnson County"),
    (r"city council", "City Council"),
    (r"parks", "Parks and Recreation Commission"),
    (r"planning|zoning", "Planning and Zoning Commission"),
    (r"board of adjustment", "Board of Adjustment"),
    (r"\btree\b", "Tree and Storm Water Advisory Board"),
    (r"police", "Police Department"),
]
DEFAULT_DEPARTMENT = "City of North Liberty"


def source_title(metadata):
    """A readable title for a document, without its web address."""
    name = metadata.get("file_name", "Unknown document")
    info = SOURCE_INFO.get(name)
    if info and info.get("title"):
        return info["title"].strip().rstrip("|").strip()
    if name.startswith("video_"):
        return " ".join(name[18:].removesuffix(".txt").split())  # video_<11-char id>_<title>.txt
    return name.rsplit(".", 1)[0]


def department(metadata):
    """Which department or board a document belongs to."""
    info = SOURCE_INFO.get(metadata.get("file_name", ""), {})
    if info.get("department"):
        return info["department"]
    url = info.get("url", "")
    for site, dept in DEPARTMENT_BY_WEBSITE:
        if site in url:
            return dept
    title = source_title(metadata).lower()
    for pattern, dept in DEPARTMENT_BY_TITLE:
        if re.search(pattern, title):
            return dept
    return DEFAULT_DEPARTMENT


def friendly_source(metadata):
    """The source label shown with passages and in answers' "Sources:" lists."""
    name = metadata.get("file_name", "Unknown document")
    label = source_title(metadata)
    if name.endswith(".pdf") and metadata.get("source"):
        label += f", page {metadata['source']}"   # the PDF reader stores the page number here
    info = SOURCE_INFO.get(name, {})
    if info.get("url"):
        return f"{label} ({info['url']})"
    if name.startswith("video_"):
        return f"{label} (video: https://youtu.be/{name[6:17]})"   # YouTube IDs are 11 characters
    return label


# Only the source line is added to the text that's searched; file details
# (path, size, dates, page numbers) are left out, since they're noise to the search.
SEARCHED_FIELDS = ("title", "department")


def label_document(doc):
    """Stamp a document with its source line before it's cut into chunks.
    Every chunk inherits it."""
    doc.metadata["title"] = source_title(doc.metadata)
    doc.metadata["department"] = department(doc.metadata)
    hidden = [k for k in doc.metadata if k not in SEARCHED_FIELDS]
    hidden.append("header_path")   # added later, when chunks are cut at headings
    doc.excluded_embed_metadata_keys = hidden
    doc.excluded_llm_metadata_keys = list(doc.metadata) + ["header_path"]   # the app adds its own labels

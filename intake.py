"""Intake: file new documents in the right collection, ready to build.

Drop files in inbox/, or add web addresses to inbox/links.txt, then run:

  python intake.py             # file everything in the inbox
  python intake.py --refresh   # download every saved web page again

Then run python build_index.py.

Where things go:
  YouTube link                     -> data/meetings/   (the video's transcript)
  any other web link               -> data/official/   (the page's main content)
  a file (PDF, text, Markdown)     -> data/official/   (the safe default)
  a meeting transcript text file   -> data/meetings/   (starts with Title / Published / Video ID)
  a file in inbox/<folder>/        -> data/<folder>/   (your choice overrides the guess)

Each document is added to sources.json, the catalog (title, web address).
The report, inbox/REPORT.md, lists what went where and anything to check.
Files the script can't handle yet stay in the inbox.

Needs: pip install -r requirements-intake.txt
For meeting dates, set a YouTube Data API key in the youtube_api environment
variable (otherwise the date is left as "unknown" and flagged in the report).
"""
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.robotparser import RobotFileParser

import requests

import sources   # department rules, so the report can show each document's department

INBOX = Path("inbox")
LINKS = INBOX / "links.txt"
REPORT = INBOX / "REPORT.md"
DATA = Path("data")
RAW = Path("sources_raw")         # originals, when what's filed is a conversion
CATALOG = Path("sources.json")

DEFAULT_COLLECTION = "official"
MEETINGS = "meetings"
FILED_AS_IS = {".pdf", ".txt", ".md"}   # Word, PowerPoint, and Excel need converters (planned)
WHOLE_PAGE = "whole-page"               # the mark in links.txt for listing pages
SHORT_PAGE = 500                        # characters; less than this gets flagged in the report
WEB_AGENT = "trafilatura"               # the name trafilatura gives when downloading pages

LINKS_HELP = """\
# Add one web address per line, then run:  python intake.py
#   YouTube links become meeting transcripts; other links become official documents.
#   Listing pages (event calendars, directories), where the links ARE the content:
#   add "whole-page" after the address, e.g.  https://example.org/calendar/ whole-page
# Lines starting with # are ignored. Addresses that are filed are taken off this list.
"""
STAYS = "It stays in the inbox."
LINK_STAYS = "It stays in links.txt."
TRANSCRIPT_START = re.compile(r"Title: .*\nPublished: .*\nVideo ID: ")


# ---- The report ---------------------------------------------------------------
class Report:
    def __init__(self):
        self.filed, self.check, self.not_filed = [], [], []

    def write(self):
        lines = [f"# Intake report, {datetime.now():%B %d, %Y at %I:%M %p}", ""]
        for heading, items, empty in (
            ("Filed", self.filed, "Nothing new."),
            ("Please check", self.check, "Nothing to check."),
            ("Not filed", self.not_filed, "Everything was filed."),
        ):
            lines += [f"## {heading}", ""] + [f"- {i}" for i in items or [empty]] + [""]
        if self.filed:
            lines.append("Next: run `python build_index.py`, then commit and push.")
        text = "\n".join(lines)
        REPORT.write_text(text + "\n", encoding="utf-8")
        print(text)


# ---- The catalog ----------------------------------------------------------------
def load_catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8")) if CATALOG.exists() else {}


def save_catalog(catalog):
    CATALOG.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")


def existing_files():
    """Every document already in data/, by file name. (The catalog is keyed by
    file name, so names must be unique across all the collections.)"""
    return {p.name: p for p in DATA.rglob("*") if p.is_file()}


def new_name(title, suffix):
    """A readable, unused file name made from a title."""
    base = re.sub(r'[\\/:*?"<>|#%]', "", title.split(" | ")[0])   # drop " | Site Name"
    base = " ".join(base.split()).strip(" .")[:80] or "document"
    taken, name, n = existing_files(), f"{base}{suffix}", 2
    while name in taken:
        name, n = f"{base} ({n}){suffix}", n + 1
    return name


def describe(name, catalog):
    """How a filed document will be labeled: its title and department.
    (main() points sources.py at this run's catalog, so new entries count.)"""
    meta = {"file_name": name}
    return f"\"{sources.source_title(meta)}\", department: {sources.department(meta)}"


# ---- Web pages ---------------------------------------------------------------
SITE_RULES = {}   # each site's robots.txt, read once per run


def site_rules(url, report):
    """A site's robots.txt rules, read once. Any Content-Signal lines (a newer
    way for sites to say how AI may use their content) go in the report."""
    site = urlparse(url)._replace(path="", params="", query="", fragment="").geturl()
    if site not in SITE_RULES:
        rules = RobotFileParser()
        try:
            r = requests.get(f"{site}/robots.txt", timeout=20, headers={"User-Agent": WEB_AGENT})
            if r.status_code in (401, 403):
                rules.disallow_all = True    # the site won't even show its rules: treat as "no"
            elif r.status_code < 400:
                rules.parse(r.text.splitlines())
                signals = sorted({line.strip() for line in r.text.splitlines()
                                  if line.strip().lower().startswith("content-signal")})
                for signal in signals:
                    report.check.append(f"{site}: the site's robots.txt says \"{signal}\". Check "
                                        f"that it allows its pages to be used to answer questions.")
            else:
                rules.allow_all = True       # no robots.txt (404 and the like): no rules
        except requests.RequestException:
            rules.allow_all = True           # couldn't reach it: no rules to follow
        SITE_RULES[site] = rules
    return SITE_RULES[site]


def robots_allow(url, report):
    """Does the site's robots.txt let us fetch this page?"""
    return site_rules(url, report).can_fetch(WEB_AGENT, url)


def final_address(url):
    """Where a web address ends up after redirects (http -> https, old -> new
    paths), so the catalog links to the page's real, current address."""
    try:
        r = requests.head(url, allow_redirects=True, timeout=20, headers={"User-Agent": WEB_AGENT})
        if r.status_code == 405:   # some sites don't answer HEAD requests
            r = requests.get(url, allow_redirects=True, timeout=20, headers={"User-Agent": WEB_AGENT})
        return r.url if r.ok else url
    except requests.RequestException:
        return url


def import_web(url, whole_page, catalog, report):
    """Download a web page into data/official/ (or update its existing copy)."""
    import html2text
    import trafilatura

    given, url = url, final_address(url)
    if url != given:
        report.check.append(f"{given} redirects to {url}; the catalog uses {url}.")

    # The same page again? Its copy is updated, wherever it's filed.
    name = next((n for n, info in catalog.items() if info.get("url") in (url, given)), None)
    path = existing_files().get(name) if name else None
    kept = f" The saved copy ({path.relative_to(DATA).as_posix()}) was kept." if path else ""

    if not robots_allow(url, report):
        report.not_filed.append(f"{url}: the site's robots.txt asks automated tools not to "
                                f"fetch this page.{kept}")
        return False
    html = trafilatura.fetch_url(url)
    if html is None:
        report.not_filed.append(f"{url}: couldn't download it.{kept}")
        return False
    if whole_page:
        text = html2text.html2text(html)      # whole page, links included
    else:
        # trafilatura finds the page's main content and drops menus, footers, and ads.
        # favor_recall=True leans toward keeping text when it isn't sure.
        text = trafilatura.extract(html, output_format="markdown", include_links=False,
                                   include_tables=True, favor_recall=True)
    if not text:
        report.not_filed.append(f"{url}: no main content found on the page. If it's a listing "
                                f"page, add \"{WHOLE_PAGE}\" after the address.{kept}")
        return False

    meta = trafilatura.extract_metadata(html)
    title = meta.title if meta and meta.title else url
    if not path:
        name = name or new_name(title, ".txt")
        path = DATA / DEFAULT_COLLECTION / name
    path.parent.mkdir(parents=True, exist_ok=True)
    status = ("new" if not path.exists() else
              "unchanged" if path.read_text(encoding="utf-8") == text else "updated")
    path.write_text(text, encoding="utf-8")
    raw = RAW / "web" / f"{Path(name).stem}.html"   # the page as downloaded
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(html, encoding="utf-8", newline="")   # exactly as downloaded

    entry = catalog.setdefault(name, {})
    entry.setdefault("title", title)   # a title edited by hand in sources.json is kept
    entry.update({"url": url, "via": "web"})
    if whole_page:
        entry["whole_page"] = True
    else:
        entry.pop("whole_page", None)
    place = path.relative_to(DATA).as_posix()
    report.filed.append(f"{place} ({status}) from {url}: {describe(name, catalog)}, {len(text):,} characters")
    if len(text) < SHORT_PAGE and not whole_page:
        report.check.append(f"{place}: very little text was kept ({len(text)} characters). If the page "
                            f"is mostly a list of links, add \"{WHOLE_PAGE}\" after its address.")
    return True


# ---- YouTube videos ------------------------------------------------------------
def youtube_id(url):
    """The 11-character video ID in a YouTube link, or None if it isn't one."""
    parts = urlparse(url)
    host = parts.netloc.lower().removeprefix("www.").removeprefix("m.")
    if host == "youtu.be":
        return parts.path.strip("/")[:11] or None
    if host.endswith("youtube.com"):
        if parts.path == "/watch":
            return parse_qs(parts.query).get("v", [None])[0]
        match = re.match(r"/(?:live|shorts|embed)/([\w-]{11})", parts.path)
        return match.group(1) if match else None
    return None


def video_details(video_id):
    """The video's title and publish date. The date needs a YouTube Data API key
    (the youtube_api environment variable); without one, the date is None."""
    key = os.environ.get("youtube_api")
    if key:
        r = requests.get("https://www.googleapis.com/youtube/v3/videos", timeout=20,
                         params={"part": "snippet", "id": video_id, "key": key})
        r.raise_for_status()
        items = r.json().get("items")
        if not items:
            raise ValueError("no such video, or it's private")
        snippet = items[0]["snippet"]
        published = datetime.strptime(snippet["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")
        return snippet["title"], f"{published:%Y-%m-%d %H:%M:%S}"
    # Without a key: YouTube's public oEmbed address gives the title, not the date
    r = requests.get("https://www.youtube.com/oembed", timeout=20,
                     params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"})
    r.raise_for_status()
    return r.json()["title"], None


def import_youtube(url, video_id, catalog, report):
    """Save a video's transcript to data/meetings/ (or update its existing copy)."""
    from youtube_transcript_api import YouTubeTranscriptApi

    try:
        title, published = video_details(video_id)
        transcript = YouTubeTranscriptApi().fetch(video_id)
    except Exception as e:   # no captions, private video, network trouble...
        report.not_filed.append(f"{url}: couldn't get the transcript ({type(e).__name__}: "
                                f"{str(e).strip().splitlines()[0] if str(e).strip() else 'no details'}).")
        return False
    full_text = " ".join(segment.text for segment in transcript)

    path = next((p for n, p in existing_files().items() if n.startswith(f"video_{video_id}_")), None)
    if not path:
        safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:80]
        path = DATA / MEETINGS / f"video_{video_id}_{safe_title}.txt"
    elif not published:   # importing it again without the key: keep the date we have
        found = re.search(r"^Published: (.+)$", path.read_text(encoding="utf-8"), re.MULTILINE)
        published = found.group(1) if found and found.group(1) != "unknown" else None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"Title: {title}\nPublished: {published or 'unknown'}\nVideo ID: {video_id}\n\n"
                    f"{full_text}", encoding="utf-8")
    entry = catalog.setdefault(path.name, {})
    entry.update({"title": title, "url": f"https://youtu.be/{video_id}", "via": "youtube"})

    place = path.relative_to(DATA).as_posix()
    report.filed.append(f"{place} from {url}: {describe(path.name, catalog)}")
    if not published:
        report.check.append(f"{place}: the meeting date is unknown (set the youtube_api key to "
                            f"get it). Add it on the \"Published:\" line.")
    if sources.department({"file_name": path.name}) == sources.DEFAULT_DEPARTMENT:
        report.check.append(f"{place}: no board or department was recognized in the title, so it's "
                            f"labeled \"{sources.DEFAULT_DEPARTMENT}\". Add a \"department\" in "
                            f"sources.json if that's wrong.")
    return True


# ---- Files ---------------------------------------------------------------------
def is_transcript(path):
    """Does this text file start like a meeting transcript (Title / Published / Video ID)?"""
    if path.suffix.lower() != ".txt":
        return False
    start = path.read_text(encoding="utf-8", errors="replace")[:500].replace("\r\n", "\n")
    return bool(TRANSCRIPT_START.match(start))


def guess_collection(path):
    """Which collection a file belongs in, and why."""
    if is_transcript(path):
        return MEETINGS, "it starts like a meeting transcript"
    return DEFAULT_COLLECTION, "that's the default for documents"


def file_title(path):
    """A title from the document itself (a PDF's information, a transcript's
    Title line), or else from the file name."""
    if is_transcript(path):
        first_line = path.read_text(encoding="utf-8", errors="replace").splitlines()[0]
        return first_line.removeprefix("Title: ").strip(), "its Title line"
    if path.suffix.lower() == ".pdf":
        import fitz   # PyMuPDF
        with fitz.open(path) as pdf:
            title = (pdf.metadata or {}).get("title", "").strip()
        if title and not title.lower().startswith(("microsoft word", "untitled")):
            return title, "the PDF's own title"
    return " ".join(re.sub(r"[_-]+", " ", path.stem).split()), "the file name"


def import_file(path, catalog, report):
    """Move a file from the inbox into its collection."""
    shown = path.relative_to(INBOX).as_posix()
    suffix = path.suffix.lower()
    if suffix not in FILED_AS_IS:
        report.not_filed.append(f"{shown}: {suffix or 'files without an extension'} can't be read "
                                f"yet (converters for Word, PowerPoint, and Excel are planned). "
                                f"Save it as a PDF and drop that in instead. {STAYS}")
        return False

    folders = path.relative_to(INBOX).parts[:-1]
    if folders:   # dropped in inbox/<folder>/: the librarian chose the collection
        collection, why = folders[0], "it was put in that folder of the inbox"
        if not (DATA / collection).is_dir():
            choices = ", ".join(sorted(p.name for p in DATA.iterdir() if p.is_dir()))
            report.not_filed.append(f"{shown}: there's no collection named \"{collection}\" "
                                    f"(choices: {choices}). {STAYS}")
            return False
    else:
        collection, why = guess_collection(path)

    target = DATA / collection / path.name
    already = existing_files().get(path.name)
    via = catalog.get(path.name, {}).get("via")
    if already and via in ("web", "youtube"):
        report.not_filed.append(f"{shown}: that name belongs to a document imported from "
                                f"{catalog[path.name].get('url', 'the web')}, which only that "
                                f"import updates. Rename this file. {STAYS}")
        return False
    if already and already != target:
        report.not_filed.append(f"{shown}: a document with the same name is already in "
                                f"{already.relative_to(DATA).as_posix()}. Rename one of them, or "
                                f"move the old one, so each name is used once. {STAYS}")
        return False
    replacing = target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(path, target)

    place = target.relative_to(DATA).as_posix()
    if path.name not in catalog:
        title, title_from = file_title(target)
        catalog[path.name] = {"title": title, "via": "file"}
        report.check.append(f"{place}: the title \"{title}\" came from {title_from}. Edit it in "
                            f"sources.json if it isn't right.")
    if not catalog[path.name].get("url"):
        report.check.append(f"{place}: no web address, so answers can't link to it. Add a \"url\" "
                            f"in sources.json where residents can find it.")
    if "department" not in catalog[path.name]:
        report.check.append(f"{place}: department guessed from the rules in sources.py. Add a "
                            f"\"department\" in sources.json if it's wrong.")
    action = "replaced the earlier copy" if replacing else f"filed in {collection} because {why}"
    report.filed.append(f"{place} ({action}): {describe(path.name, catalog)}")
    return True


# ---- Running it ----------------------------------------------------------------
def read_links():
    """The addresses in links.txt: (line, address, whole_page) for each."""
    if not LINKS.exists():
        return []
    found = []
    for line in LINKS.read_text(encoding="utf-8").splitlines():
        words = line.split()
        if words and not line.lstrip().startswith("#"):
            found.append((line, words[0], WHOLE_PAGE in words[1:]))
    return found


def intake(catalog, report):
    keep = []   # links that weren't filed stay on the list
    for line, url, whole_page in read_links():
        video_id = youtube_id(url)
        if video_id:
            done = import_youtube(url, video_id, catalog, report)
        elif url.startswith(("http://", "https://")):
            done = import_web(url, whole_page, catalog, report)
        else:
            report.not_filed.append(f"{url}: not a web address (it should start with https://).")
            done = False
        if not done:
            keep.append(line)
            report.not_filed[-1] += f" {LINK_STAYS}"
    LINKS.write_text(LINKS_HELP + "".join(f"{line}\n" for line in keep), encoding="utf-8")

    for path in sorted(INBOX.rglob("*")):
        if path.is_file() and path not in (LINKS, REPORT) and not path.name.startswith("."):
            import_file(path, catalog, report)


def refresh(catalog, report):
    """Download every web page in the catalog again, so the copies stay current."""
    for name, info in list(catalog.items()):
        if info.get("via") == "web":
            import_web(info["url"], info.get("whole_page", False), catalog, report)


def main():
    INBOX.mkdir(exist_ok=True)
    catalog, report = load_catalog(), Report()
    sources.SOURCE_INFO = catalog   # titles and departments come from this run's catalog
    if "--refresh" in sys.argv[1:]:
        refresh(catalog, report)
    else:
        intake(catalog, report)
    save_catalog(catalog)
    report.write()


if __name__ == "__main__":
    main()

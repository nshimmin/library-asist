# Implementation Guide: Library & City Info Assistant

A guide for other libraries and communities to set up their own copy of this assistant. It's a living document, updated as the North Liberty prototype develops. Last updated Nov 17, 2026.

**Status:** prototype. Being tested at North Liberty Public Library (Iowa) before staff rollout. Expect changes.

---

## 1. What this is

A chat assistant that answers questions about your library and local government **from your own documents**: policy manuals, meeting recordings, web pages, and a staff FAQ. Every answer cites its sources, so residents can check it.

Technically it's a **retrieval-augmented (RAG) assistant**: it searches your documents first, then has an AI language model write the answer from what it found. The language model is one swappable part. Everything is built from open-source software and **open-weight** AI models.

**Cost:** $0 to run as a prototype (free tiers of GitHub, Streamlit Community Cloud, and Groq).

---

## 2. What's included

### Accounts you'll need (all free)

| Service | What it does | Notes |
|---|---|---|
| **GitHub** | Stores the code and documents | Public repository |
| **Streamlit Community Cloud** | Runs the chat app on the web | Sign in with GitHub |
| **Groq** | Runs the AI language model | Free tier: ~1,000 requests/day, 8,000 tokens/minute |
| **GitHub Codespaces** | Browser-based workspace for import scripts and building the index | Free monthly hours; included with GitHub |

### Software packages

**Used by the app** (listed in `requirements.txt`, installed automatically by Streamlit):

| Package | Purpose | License |
|---|---|---|
| `streamlit` | Chat web interface | Apache 2.0 |
| `llama-index` | Search and agent framework | MIT |
| `llama-index-llms-groq` | Connects to the Groq-hosted model | MIT |
| `llama-index-llms-openrouter` | Optional: connects to OpenRouter (e.g., the fully open OLMo model) | MIT |
| `llama-index-embeddings-huggingface` | Runs the embedding model (meaning search) and the reranker | MIT |
| `llama-index-retrievers-bm25` (brings `bm25s`, `PyStemmer`) | Keyword search | MIT |
| `llama-index-readers-file` + `pymupdf` | Reads PDFs | MIT / AGPL* |
| `requests` | Sends gap-log notes to GitHub | Apache 2.0 |

*Check PyMuPDF's license terms for your use; it's dual-licensed.

**Used only for adding documents** (`intake.py`; listed in `requirements-intake.txt`, not needed by the app):

| Package | Purpose | License |
|---|---|---|
| `trafilatura` | Downloads web pages and keeps only the main content (drops menus, footers) | Apache 2.0 |
| `html2text` | Saves a whole page as text, links included (for listing pages) | GPL 3.0 |
| `youtube-transcript-api` | Gets the captions of meeting videos (see the note in section 9) | MIT |
| `torch` (CPU version) | Needed to build the search index | BSD |

**Planned:** pin exact package versions (or a lock file) before packaging. Unpinned installs can stall for a long time while pip works out which versions fit together.

### AI models

| Model | Role | Openness |
|---|---|---|
| `openai/gpt-oss-120b` (via Groq) | Writes the answers | Open-weight (Apache 2.0) |
| `BAAI/bge-small-en-v1.5` | Meaning search: turns text into "meaning fingerprints" | Open (MIT) |
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | Reranker: re-scores the top search results more carefully | Open (Apache 2.0) |
| `allenai/olmo-3.1-32b-instruct` (optional, via OpenRouter) | Fully open alternative (open weights, training data, and code) | Apache 2.0 |

The embedding model and reranker download once from Hugging Face and run inside the app; no account needed.

### Files in the repository

| File / folder | What it is |
|---|---|
| `app.py` | The chat app (prompt, search tool, answer display) |
| `sources.py` | Titles, web links, and departments for every document (the source line), plus the department rules to edit for your community |
| `docs/` | This guide, the project notes, and the test questions |
| `search.py` | **All search settings in one place:** models, chunking, how many passages, the not-found cutoff. Shared by the app and the scripts so they always match. |
| `requirements.txt` | Packages the app needs |
| `data/` | Your documents. **Each folder is one collection** with its own search tool: `data/official/` (policies, web pages, staff FAQ) and `data/meetings/` (meeting transcripts). |
| `storage/` | The search index built from `data/` (commit it; don't let the app rebuild it). `storage/build_manifest.json` records each document's fingerprint, collection, and chunk count. |
| `sources.json` | "Card catalog": a readable title and web link for each document |
| `build_index.py` | Updates `storage/` from `data/`, processing only new, changed, or removed documents (`--full` rebuilds everything) |
| `intake.py` | Files new documents: drop files in `inbox/` or add links to `inbox/links.txt`, and it puts each in the right collection, adds it to `sources.json`, and writes a report (`inbox/REPORT.md`). `--refresh` downloads every saved web page again. |
| `inbox/` | Where new documents go (`links.txt` for web addresses) |
| `sources_raw/` | Originals of converted documents (web pages as downloaded) |
| `check_search.py` | Shows what the search finds for a question, step by step, with scores (no AI cost) |

---

## 3. Setup, step by step

1. **Copy the repository** to your own GitHub account.
2. **Replace the documents** in `data/official/` and `data/meetings/` with your own (see section 4), and list your web pages and meeting videos in `inbox/links.txt` (section 5).
3. **Edit the library name** in `app.py` (the system prompt and title). *A settings file to make this easier is planned.*
4. **Build the index** in Codespaces (see section 5), then commit `data/`, `sources.json`, and `storage/`.
5. **Get a Groq API key** at console.groq.com.
6. **Deploy on Streamlit Community Cloud:** New app → your repo → branch `main` → main file `app.py`. Under **Advanced settings**, choose **Python 3.12** (newer versions may break packages), and paste your secrets:
   ```toml
   groq_api = "your-groq-key"
   ```
   Python version can only be chosen when deploying. To change it, delete and redeploy.
7. **Test** with a set of questions you know the answers to (see section 6).

**Optional secrets:**
- `openrouter_api`: switches the model to OLMo via OpenRouter (costs fractions of a cent per question).
- `github_token` + `gap_issue_number`: turns on the gap log (section 7).

---

## 4. Choosing documents

**Good sources are:**
- **Official and public:** published by the library or city, so residents can verify them.
- **Citable:** have a stable web address to link to.
- **Maintained:** kept current by whoever is responsible.

**Examples that work well:** policy manual (PDF), library web pages, city boards & commissions page, meeting video transcripts, and a **staff-maintained FAQ**.

**One home for each fact.** If information is already in an official document or page, let the assistant find it there. Copying it into the FAQ creates a second version that goes out of date. When the official wording is unclear, incomplete, or wrong, fix it at the source.

**Keep sources consistent.** If two documents disagree (a web page and the policy manual giving different limits), the assistant is handed both and may quote either. Search results showing a contradiction are a sign to fix a source, not the search.

**Prefer PDFs over Word files** for policy manuals. Answers cite PDF page numbers, which residents can check; Word files have no pages. (Best of all is text with headings; converting PDFs that way is planned.)

**Time-sensitive information** (upcoming events, next meeting dates) is best read live from an official calendar or feed, not saved into the index, which goes stale. **Meeting transcripts record what was said, not a schedule:** "our next meeting is the 11th" means a different month by the time someone asks.

**Staff FAQ tips:**
- **Only for information published nowhere else** (e.g., notary services, a discontinued service people still ask about).
- Name it descriptively (e.g., `Library Services FAQ.txt`); the file name becomes the source label.
- Give each entry a `##` question heading (each becomes its own search chunk) and an **"Also asked as"** line with the words patrons use. Keyword search only matches words with the same root: "notary" and "notarized" don't match each other.
  ```
  ## Q: Can I get something notarized at the library?
  Also asked as notary, notary public, notarize, notarization
  A: Yes, with a couple of exceptions...
  ```
- **"No" entries are valuable.** The assistant may only say "no" when a document says so. For a discontinued service people still ask about (North Liberty's old driver's license kiosk), an entry that clearly says no, and where to go instead, gives a correct answer where outdated unofficial pages still say otherwise.
- Staff-confirmed facts only; the assistant repeats them closely.
- Add it to `sources.json` with a link to the file on GitHub.

**Avoid:** social media posts (unofficial, hard to cite, go stale). Pages that build their content with JavaScript (like many event calendars) can't be imported; use an RSS feed or export instead.

---

## 5. Routine tasks

**Working in Codespaces:** on your repo, choose Code → Codespaces → Create codespace on main. In the terminal, install what you need:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt -r requirements-intake.txt
```

Don't add a custom `.devcontainer` setup file. Custom setup images repeatedly froze while downloading; GitHub's default image starts quickly. Stop the codespace when done (it uses free monthly hours).

**Adding or updating documents:**
1. `git pull`
2. Drop files in `inbox/` and add web addresses to `inbox/links.txt`, then run `python intake.py`. Read `inbox/REPORT.md`: it lists where each document went and anything to check (a title taken from the file name, a missing web address, a guessed department).
3. `python build_index.py`. It only processes documents that are new, changed, moved, or removed, and lists them. The first build (or `python build_index.py --full`) does everything and is slow; after that a small edit takes seconds.
4. `python check_search.py "a question about the new content"` to confirm it's found.
5. Commit and push `inbox`, `data`, `sources_raw`, `sources.json`, and `storage`.
6. The app notices the new index and reloads it on its own.

**What needs a rebuild:**

| What you changed | Rebuild? |
|---|---|
| `app.py` (prompt, tool description) | No. The app restarts on its own after a push. |
| Anything in `data/` (FAQ, policy manual, web pages), or a title or department in `sources.json` | Yes: `build_index.py` (only the affected documents), then push. |
| Embedding model or chunk sizes (`search.py`), department rules (`sources.py`) | Yes. `build_index.py` rebuilds everything on its own, since every chunk changes. |

**What `intake.py` does with each item:**

| Item | Goes to | How |
|---|---|---|
| YouTube link | `data/meetings/` | The video's captions, with its title, date, and video ID at the top |
| Other web link | `data/official/` | The page's main content (menus and footers dropped); the page as downloaded is kept in `sources_raw/web/` |
| PDF, text, or Markdown file | `data/official/` | Filed as it is (PDFs stay PDFs, so answers can cite page numbers) |
| Text file that starts like a transcript (`Title:` / `Published:` / `Video ID:`) | `data/meetings/` | Filed as it is |
| A file in `inbox/<folder>/` | `data/<folder>/` | Your choice overrides the guess |
| Word, PowerPoint, Excel | stays in the inbox | Converters are planned; save it as a PDF for now |

Each document gets a catalog entry in `sources.json` (title, web address, and `via`: web, youtube, or file). Dropping a file with the same name as an earlier file replaces it (a new version of the FAQ, say); a web page or transcript can only be updated by importing its link again.

**Adding a web page:**
1. Add its address to `inbox/links.txt` and run `python intake.py`. Skim the saved file in `data/official/`.
2. Most pages: done. trafilatura keeps the main content and drops menus and footers.
3. **Listing pages** (event calendars, staff directories, lists of databases) are different: their links *are* the content, and trafilatura drops link text. If the saved file is missing titles or names, add the address again with `whole-page` after it. That page is then saved whole (marked `"whole_page": true` in `sources.json`).
4. **Keeping pages current:** `python intake.py --refresh` downloads every saved web page again; the report says which ones changed.

**Rules the intake follows:** it reads each site's `robots.txt` and won't download pages the site asks automated tools not to fetch (the report says so, and any saved copy is kept). If the site's `robots.txt` has a `Content-Signal` line (how the site says AI may use its content), the report shows it so you can decide. If an address redirects (`http://` to `https://`, or an old path to a new one), the catalog stores the final address. A title you edit by hand in `sources.json` is kept when the page is downloaded again.

**Meeting dates:** the date at the top of a transcript comes from the YouTube Data API, which needs a free API key in the `youtube_api` environment variable. Without one, the date is left as "unknown" and flagged in the report.

**Collections:** each folder in `data/` is one collection, searched by its own tool, so the many meeting transcripts can't crowd out official answers. To move a document to another collection, move its file to that folder and run `build_index.py`. Files left directly in `data/` are treated as official.

**How the build knows what changed:** `build_index.py` keeps a fingerprint (a SHA-256 code) of each file in `storage/build_manifest.json`, along with its collection, title, and department. If any of those differ next time, that document's old chunks are removed and it's processed again. Windows and Linux line endings are treated the same, so building on another computer doesn't reprocess everything.

**How documents are chunked:** `build_index.py` first cuts documents at their headings (`#`, `##`…), then splits any section that's still long into ~512-token pieces. Pages with headings (web pages, a heading-style FAQ) get one chunk per section; documents without headings (transcripts, PDFs) are split by size only.

**Build messages you can ignore:**
- `404 Not Found` for `additional_chat_templates` or `2_Normalize/config.json`: the loader checks for optional files the model doesn't have.
- `You are sending unauthenticated requests to the HF Hub`: fine for downloading small public models.
- `The fitz API is deprecated`: a note for the PDF package's maintainers.
- In general, `INFO` and `WARNING` lines are commentary. A real failure stops the build with a `Traceback` and an error message.

**Git habits:** always `git pull` before starting and before pushing. If a push is rejected as "behind," run `git pull --rebase`, then `git push`.

---

## 6. Testing

- Keep a list of 10+ questions with known right answers, including some the documents **don't** cover (the assistant should say "I couldn't find anything about…", never "no"). Don't use the prompt's own worked example as a test question.
- Ask each question **2–3 times**; answers vary from run to run. Score each ✅ / ⚠️ / ❌ before and after every change. **Change one thing at a time** so you know what helped.
- **For any miss, open "How I found this"** under the answer. It shows the assistant's actual search query and the passages it was given. Wrong passages = a search problem; right passages, wrong answer = an answer problem.
- **The assistant writes its own search query**; it doesn't search your exact words. Run `check_search.py` with the query from the "Searched for" line, not just your own wording. (North Liberty's notary miss came from the assistant adding "North Liberty Library" to its query.)
- `check_search.py` output: `->` marks passages handed to the model; `M#3` / `K#1` show where meaning and keyword search ranked each one; the score is the reranker's (passages below the cutoff are dropped).
- When a question keeps failing, check whether a good source for it exists at all. Sometimes the fix is better information, not better search.

---

## 7. Built-in features

- **Source line:** every chunk is stamped with its document's title and department (e.g., "Room Reservations / Library"), so a section keeps its context and the search can tell boards apart. On pages that cover several boards, each section gets its own department from its heading.
- **Two collections:** official documents and meeting transcripts are searched by separate tools, so transcripts (most of the text) can't crowd out official answers. Each collection is a folder in `data/` (`official/`, `meetings/`). The assistant picks the tool from each tool's description; "How I found this" shows which it used.
- **Hybrid search:** meaning search and keyword search each find candidates; the lists are merged, a reranker re-scores them, and only passages above a cutoff go to the model (up to 5). Weak matches are dropped, which is what lets the assistant say "I couldn't find anything."
- **Source citations:** every answer ends with a "Sources:" list with links, limited to passages actually used.
- **"How I found this":** under each answer, the search query and passages, so anyone can check how an answer was made.
- **Today's date:** sent with each question so "next meeting" questions work.
- **"Not found" isn't "no":** when documents are silent, the assistant says so and suggests asking staff.
- **Gap log (optional):** questions the assistant couldn't answer are posted (question and time only) as comments on a GitHub Issue. Use this to decide what content to add. Setup: create an issue, create a fine-grained GitHub token with Issues read/write on your repo only, and add `github_token` and `gap_issue_number` to Streamlit secrets. Renew the token before it expires.

**Steering the assistant:** the search tool's description in `app.py` (the text under `async def search_documents`) is read by the assistant every time it decides how to search. North Liberty's tells it to write short queries from the key words, keep department and board names, and not add the town's name (everything is about the community, so the name doesn't narrow anything). **Give example queries, not just rules:** a rule alone ("don't add words") led the assistant to drop "library" from "library board meeting."

---

## 8. Privacy

- Log only question text, date, and time. Nothing identifying who asked.
- Patron question logs may be confidential library records under state law (in Iowa, Iowa Code §22.7(13)). Check your state's rules.
- Before staff or public use, keep logs in a private location, not the public repo, and tell users that questions are logged to improve the tool.

---

## 9. Known limitations (current prototype)

- `intake.py` and `build_index.py` are run by hand in Codespaces. Planned: run automatically by GitHub Actions when something lands in the inbox.
- Word, PowerPoint, and Excel files can't be added yet (save them as PDFs); converters are planned.
- **Meeting transcripts come through `youtube-transcript-api`,** which reads YouTube's captions the way the YouTube player does, not through an official, documented feed, so it could stop working without notice. The official route is the YouTube Data API's captions download, which needs the channel owner (usually the city's communications staff) to sign in. Worth arranging with them.
- The index is stored as files in the repository; GitHub's 100 MB file limit will eventually require a small database file for large collections.

- Meeting transcripts are automatic captions: messy, and they use relative dates ("next month"). The prompt forbids taking dates, fees, or rules from them as current.
- Each question stands alone; the assistant doesn't remember the previous one yet, so it can't ask and follow up on a clarifying question.
- Groq's free tier allows about one question per minute.
- Event calendars and meeting schedules need live feeds (planned).
- Questions are sent to Groq's servers; an offline/local option is a future goal.

---

## 10. Lessons learned

- Smaller AI models often fail at "tool calling" (deciding to search). gpt-oss-120b handles it well.
- Set the embedding model explicitly, or LlamaIndex silently falls back to OpenAI and errors.
- Streamlit shows text between two `$` signs as math; the app escapes dollar signs.
- Website navigation menus pollute search; import only each page's main content.
- **But check what the footer held.** Dropping menus and footers also dropped North Liberty's hours, address, and phone number, which appeared in every page's footer. The fix is to import the page where that information is the main content (here, the Contact page). A very short page (like a bare "Hours" page) can fail the other way: the extractor can't tell its content from the menu and keeps the menu.
- Main-content extractors drop link text, which removes event titles from calendars; save listing pages whole.
- Splitting at headings keeps each topic (e.g., each city board) in its own chunk.
- Measure before tuning: look at real search scores before choosing settings.
- The chat model only sees what search hands it; switching chat models can't fix passages search never finds.
- A bigger reranker judged better but was far too slow on free hardware (~28 s per question).
- Keyword search finds specific terms (fax, "$3 free") that meaning search misses; use both.
- **The assistant's search wording matters as much as the documents.** Extra words like the town's name make every passage look relevant and bury the right one.
- **Each model has habits.** gpt-oss adds citation marks like `【1】` unless the prompt says not to.
- **Two official sources that disagree** will produce inconsistent answers; fix the source.
- **Splitting the collection beat cutting smaller chunks.** When 90% of the text is one kind (transcripts), searching it separately helps more than any chunk-size tweak.
- **Labels can tip the balance.** Adding "Library" to every policy manual chunk's label pushed down a city page's library board section until that section got its own label. After any labeling change, re-run the test questions.
- **Bundling several changes into one test makes failures hard to explain.** Change one thing, test, then the next.

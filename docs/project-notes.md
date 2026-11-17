# Library Assistant — Project Notes

Running notes for the North Liberty library/city RAG assistant (GitHub: `nshimmin/library-asist`, hosted on Streamlit Community Cloud). Last updated Nov 17, 2026.

**Working principles:**
- Avoid temporary fixes. Wait until a good, lasting fix is possible.
- End goal: package this so other communities and libraries can implement it as easily as possible. Keep the **Implementation Guide** (project doc) current with how-tos and everything included.

## Roadmap

- **Now (next few weeks):** Nick uses and improves the app himself as the main tester.
- **Milestone 1:** Hand off to library staff for testing and use. Staff only, not the public.
- **Later:** Public use, once it's been well tested.
- **Future phase:** Make it easy for other libraries to copy (settings file for library name, documents, and prompt).

**Resident input sources (planned):** audio transcripts and Pol.is surveys.

## Next up (updated Nov 17)

**Done Nov 4:** heading-aware chunks, hybrid search (meaning + keyword), reranker (MiniLM) with a score cutoff, passages handed to the model with source labels, and the "How I found this" panel.
**Done Nov 13:** notary and driver's license FAQ entries; Room Reservations page corrected; November 2026 policy manual; short-query tool description; no citation marks.
**Done Nov 16:** official documents and meeting transcripts searched separately (PR #4); automatic reload of a new index; example queries in tool descriptions.
**Done Nov 17:** interface styling (PR #6); source line on every chunk (PR #5, rebuilt): not-found questions now score about −11, far below the −7 cutoff; section-level departments on the Boards & Commissions page (PR #7): trustees section back to #2 for "library board meeting." See the decisions log.

**Where the work happens (Nov 17):** building and testing in **Claude Code inside the Codespace** (it can run the build and `check_search.py` itself); planning and design conversations in the claude.ai Project. Project docs moved to the repo's `docs/` folder so both can use them.

### Document intake ("front door"), in this order
1. **Folders as collections, plus incremental builds.** *(Built Nov 17 on branch `folder-collections`; see the decisions log.)* Each folder in `data/` is one collection with its own search tool (`official/`, `meetings/`, `city_code/`), replacing the file-name rules (`video_`, `code_`). Builds remember a fingerprint of each document and only process new or changed files, so a large document costs its build time once and a small edit takes seconds.
2. **One import script with an inbox.** Librarians drop any file in `inbox/` (or add a link to `inbox/links.txt`). The script identifies what it is (YouTube link → meetings; web link → official; code-of-ordinances layout → city code, split by chapter; transcript layout → meetings; anything else → official, the safe default), converts it to text with headings, files it in the right collection, adds its title, department, and link to `sources.json`, keeps the original in `sources_raw/`, and writes a report flagging anything it wasn't sure about. Replaces `webimport.py`, `youtubeimport.py`, `pdfimport.py`, and the code splitter. First real test: City Code Chapter 22.
3. **Automatic builds with GitHub Actions** (free for public repositories): when something lands in the inbox or `data/`, run the import script and the build, then commit the index; the app reloads on its own. Include simple checks that warn (never move files): a transcript-looking file outside meetings, a code chapter outside city code. Plus a build report listing every document's collection, title, department, and chunk count (a shelf list).
4. **Converters and the settings file.** pymupdf4llm for PDFs (headings and page numbers), MarkItDown for Word, PowerPoint, and Excel. Folder descriptions (which tell the assistant when to search each collection) and department rules go in the settings file for other libraries.

**Scaling limit to plan for:** the index is saved as files in the repo (16 MB at 1,201 chunks). GitHub rejects single files over 100 MB, which a library with years of meeting videos would eventually reach. Fix when needed: a small database file built for this kind of search.

### Before staff testing (milestone 1)
- Move the gap log out of the public repo; confirm the Iowa Code §22.7 question with the director.
- Decide on rate limits: Groq's free tier allows about one question a minute in total (a small paid tier, or "one at a time" expectations).
- A one-page staff guide (what it covers, what it doesn't, how to report a bad answer), and ideally a "this answer was wrong" button feeding the private log.

### Other open items
- **"Ask when unclear" (Nick, Nov 13).** When a question doesn't say which department and the passages cover more than one, the assistant asks. Search first, ask only if results disagree. Department labels are now in place; still needs conversation memory (browser session only, never saved) and a prompt rule. Test case: "Can I renew my license?"
- **Routing tests** in the test set (which tool the assistant picks), including the mixed question and the advisory-board question.
- **FAQ usage counter.** A second GitHub issue; each answer citing the FAQ adds a comment (question and time only). Data for the website team.
- **Embedding model upgrade experiment** (e.g., bge-base), measured with `check_search.py`. One change at a time.
- **Compare chat models using the test set.** gpt-oss-120b (current), Qwen 27B on Groq ("preview"), OLMo 3.1 32B via OpenRouter (fully open). Make the Groq model name a Streamlit secret.
- **Show sources without relying on the model.** The app could display the source list itself.
- **Pin package versions before packaging** (an unpinned install stalled 15+ minutes on Nov 4).
- **Optional `run_tests.py`** to run the test set automatically and save a report.

## Search diagnosis

**Nov 3 (from `check_search.py`):**
- **Scores bunch together.** With bge-small, right answers scored about 0.65–0.79; not-found questions (telescope, passport photos) topped out around 0.60–0.64. A score cutoff alone can't separate good from bad.
- **Website menus polluted results.** About half of each saved library page was the navigation menu ("Library Board," "Event Calendar"…). Fixed Nov 4 with trafilatura.
- **Meeting transcripts crowd out direct answers.**
- **The staff FAQ searches very well** (0.791 for notary).

**Nov 4:**
- **Correction:** the trustees *were* being found after cleanup. Their chunk started with the end of the previous board's section, so the 65-character preview looked like the wrong board. Heading-aware chunks fix this.
- **trafilatura dropped event titles** from the WhoFi calendar (titles are links). Fixed with `WHOLE_PAGE_URLS`: listing pages are saved whole with `html2text`.
- **Keyword search finds specific terms meaning search misses** (fax, "$3 free").
- **"When is the next library board meeting?" needs a better source,** not just better search (Nick's observation). The boards page gives only a rule ("usually meets the third Monday"); there's no official calendar of actual upcoming meeting dates in the documents. See "Waiting on others / sources needed."
- **The chat model can't fix search misses**: it only sees what search hands it. A bigger embedding model might help ranking; tested later, separately.

**Nov 4, full baseline (see Test Questions doc):**
- **Same score on both runs for every question,** so the misses are systematic.
- **Transcripts still crowd out official sources.** For Q1 the model took "the 11th" from another board's "next meeting" talk and stated it as the Library Board's date. The "third Monday" rule is inside the trustees chunk (mostly names), so it wins for "who is on the board" but loses for "when is the next meeting." The bylaws say the board meets ten times a year on dates set at its annual meeting. Keyword search for "kids programs" returns only transcripts (Q10).
- **Keyword search depends on word roots.** The stemmer trims "notarized," "notarize," and "notarization" to `notar` but "notary" to `notari`. A "notary" query barely matches the FAQ.

## Waiting on others / sources needed

These are parked until an official, lasting source is available. No temporary workarounds.

- **WhoFi events RSS feed (needs approval)** → then build the events tool (see "Events calendar").
- **CivicClerk meeting data (upcoming board and commission meetings, agendas)** → then build a meeting-schedule tool (Q1). The city publishes meetings through a CivicClerk portal, which is a JavaScript app the web import can't read. Its behind-the-scenes data feed is undocumented, so we won't build on it without permission.
  - **Nov 4:** Nick subscribed to CivicClerk notifications to see whether they include stable links (e.g., to agenda PDFs or calendar files) that could serve as an official source.
  - **If not:** ask the city clerk's office (or whoever manages the portal) whether there's an official feed or export (RSS, iCal, data export), or permission to use the portal's data feed and whether CivicPlus documents it.
  - Older meeting pages and agenda packets on `northlibertyiowa.org/meetings/…` are an archive from before CivicClerk. (The boards page is on `northlibertyiowa.gov`; confirm which domain is current.)
  - Until then: Q1 is a known source gap. The assistant can cite the "usually meets the third Monday" rule but shouldn't present it as a confirmed date.
- **Fax needs a clear home in an official document (Q8).** The only mention anywhere is one sentence in the Proctoring policy (Policy Manual p. 23, item G: "Faxing services are provided at no cost"), so answers tie faxing to exam proctoring. No search change can fix what the document doesn't say. Lasting fix: a line about faxing in the policy manual's Equipment Use section at its next revision, or on the services page below. Not duplicated in the FAQ.
- **City Code, Chapter 22 "Public Library" (source candidate, Nov 16).** Defines the library board's powers (the bylaws, p. 29, point to City Ordinance 08-21). The policy manual calls the board "advisory" (p. 4) while nearly every policy says "Reviewed/Approved by the Library Board of Trustees," so the documents alone can't say what the board can do. The code is hosted by American Legal Publishing (`codelibrary.amlegal.com/codes/northliberty/…`), linked from the city's Codes & Ordinances page. **Nov 16: robots.txt checked.** It blocks AI training crawlers by name and, for everyone else, sets `Content-Signal: search=yes, ai-train=no, use=reference`. It says nothing either way about `ai-input` (feeding content to an AI for answers, which is what this assistant does). Not a clear permission, so we don't import from American Legal's site. **Nov 16:** Nick obtained the full code as a text file; its own notice (Iowa Codification, Inc.) permits copies for the city's officials, employees, and citizens. **Nick's decision: the code is public and fine for reference use** (helping people find the law as it exists). Removed from `data/` for now (as one file it would be 815 chunks against 123 official ones); it will come back **in blocks** through the import script, as its own "city code" collection with one file per chapter and one chunk per section, starting with Chapter 22. Section 22.03 settles the board question: the board has "charge, control and supervision of the library… subject to approval of the City Council." **Future (sustainability):** ask the city clerk about permission for the live online code (`ai-input`) or update alerts when the code is amended, so the copy doesn't go stale.
- **Library services page on the official website** (notary, fax, printing, scanning, etc.). Nick has little say over website content, so the gap log and FAQ usage counts will provide the data to make the case. When a page is published, add it with `webimport.py`, point the matching FAQ entries to it, and rebuild the index.

## Future tasks, goals, and ideas

- **Events calendar tool** once the WhoFi RSS feed is approved. Build `get_upcoming_events`, then remove the snapshot. See "Events calendar" below.
- **Meeting-schedule tool** once an official CivicClerk source is available. Same live-tool approach as events (read live, upcoming only, today's date). Agendas would also add written meeting content alongside the video transcripts.
- **Remove the temporary WhoFi snapshot** (`web_8.txt`) once the events tool replaces it: take the URL out of `webimport.py` (and `WHOLE_PAGE_URLS`), delete its entry from `sources.json`, delete `data/web_8.txt`, and rebuild the index.
- **Add the services page** once it's on the library website.
- **Move the gap log and FAQ counter to a private location before staff or public use** (see Privacy below).
- **Try Sensemaker for theming resident input.** Run its topic-discovery step on a small practice file (made-up comments or a public Pol.is dataset) in Codespaces, using gpt-oss-120b on Groq, **not** its Gemini default. See the Sensemaker section below.
- **Convert resident input to Sensemaker's format.** Small scripts to turn Pol.is exports and audio transcripts into a `participant_id` / `survey_text` CSV.
- **Combine themes with local information.** Connect Sensemaker's themes to the app's document search (meeting minutes, policy, history) to produce one report for the council (proposal Q22).
- **Feedback loop.** Record the council's response and show residents how their input was used (proposal Q22).
- **Private storage for resident input.** Pick a place outside the public repo before collecting real input.
- **Offline version.** Run on library hardware with a local open model. See the offline section below.
- **Public-interest model hosting.** Consider Public AI (OLMo, Apertus) instead of Groq, especially once resident input is involved.
- **Add an open-source license** once code ownership is confirmed with the library or city. See License notes.
- **Settings file for other libraries** (library name, documents, prompt), so each community can own its own copy (proposal Q23). Should include the community's name and its **historical place names**.
- **Community history collection.** When local history is added (e.g., the archive.org oral histories), give it its own collection and search tool, like the meetings split. In history, place names and eras are often the question, so its tool description should keep them (the present-day tools tell the assistant not to add the town's name). Don't strip the town's name in code, since that would break history searches.
- **Place names reference.** A short document listing each historical name of the community, its era, and what it's called now. Keyword search can't connect an older name to "North Liberty"; this document bridges them and is useful to patrons too. Same idea as the FAQ's "Also asked as" line.

## Content sources: what makes a good one

- **Official and public:** published by the library or city, so residents can check it (proposal Q23).
- **Citable:** has a stable web address the answer can link to.
- **Maintained:** kept current by the people responsible for it.
- **One home for each fact.** If information is already in an official document or page, the assistant should find it there; copying it into the FAQ creates a second version that goes out of date. When the official wording is unclear or incomplete, fix it at the source.
- **"No" entries are useful too.** A discontinued service people still ask about (the old driver's license kiosk) gets an FAQ entry that clearly says no, since outdated unofficial pages still say otherwise. It's the only way the assistant may answer "no": a document must say so.
- **Staff FAQ (only for information published nowhere else, e.g., notary, driver's license kiosk):** meets these when entries are staff-confirmed, the file is public (linked on GitHub), and it's kept up to date. It's the library's own documentation, not a stopgap. Short Q&A entries also search very well, especially when they include the words patrons use ("Also asked as:").
- **Time-sensitive information** (events, upcoming meeting dates) needs a live official source (feed/calendar), not a saved snapshot. **Meeting transcripts are a record of what was said, not a schedule:** their "next meeting is on the 11th" means a different month by the time someone asks.
- **Vendor platforms** (WhoFi, CivicClerk) often hold the official data but show it through JavaScript apps. Use their official feeds or exports, or get permission; don't build on undocumented feeds that can change without notice.
- Social media posts don't meet these. When information exists only there, the lasting fix is getting it published on the official site, which helps patrons directly too.
- The gap log and FAQ counter show which information matters most to people, which makes a good case to the website team for what to publish.
- **When a question keeps failing, check whether a good source exists at all.** Sometimes the fix is better information, not better search.

## Privacy

- **Library records are generally public, but patron records likely aren't.** Iowa Code §22.7(13) keeps library records confidential when they would reveal the identity of a patron requesting "an item or information from the library." A log of patron questions may fall under this. Confirm with the director (not legal advice).
- **Design rule:** log only the question text, date, and time. No names, emails, IP addresses, or anything identifying who asked. Applies to both the gap log and the FAQ counter.
- **Before staff or public use:** move the logs out of the public repo (e.g., a private repository just for logs), and tell users that questions are logged to improve the tool. Questions can contain personal details ("my son Jake needs…").
- **Resident input** (audio transcripts, Pol.is) needs the same care: private storage, nothing identifying in the public repo.

## Choosing a model (notes, Nov 2, 2026)

- **A model's training date matters less here.** With RAG, answers come from the documents, not the model's memory. What matters is reliable tool calling, following instructions, and sticking to the passages.
- **gpt-oss-120b is still the strongest option on Groq's free tier** and was picked partly for size; smaller models garbled tool calls in earlier testing.
- **Groq free tier (Sept 2026):** gpt-oss-120b, gpt-oss-20b, Llama 3.3 70B (older, more restrictive license), Llama 3.1 8B, and a newer Qwen 27B listed as "preview" (could change or disappear).
- **All candidates are open-weight**, so any of them meets proposal Q20.
- **What it is:** a retrieval-augmented (RAG) assistant built on an open-weight language model. The LLM is one swappable part; the documents, search, agent, and app around it are what make it local and checkable.
- **Two models, two jobs:** the embedding model decides what gets *found*; the chat model only writes from what it's given. Search problems are fixed in the data, chunking, and search steps (or with a better embedding model), not by switching chat models.
- **Model habits show up in answers.** gpt-oss was trained to cite web results with marks like `【1】`; the prompt has to ask it not to. Expect each model to have its own quirks when comparing.

## Events calendar (WhoFi)

- **Current: a snapshot is in the document index.** The WhoFi home page (`northliberty-ia.whofi.com/`, saved as `web_8.txt`) gives about a month of event listings with titles, dates, times, and audience tags. It's on `WHOLE_PAGE_URLS`, so it's saved whole (trafilatura would drop the event titles).
  - It goes stale as events change. Refresh by re-running `webimport.py` and `build_index.py`.
  - **Known weakness (Q10):** the saved text is messy, and search cuts it into chunks that mix kids' and adult events. Accepted until the RSS tool replaces it.
- **The `/calendar` page itself can't be imported.** It loads events with JavaScript, and the site asks automated tools not to crawl it.
- **Long-term: WhoFi's RSS feed (needs approval).** WhoFi provides a calendar RSS feed (pattern `.../calendar/rss/`) with each event's title, date, description, image, and link. WhoFi support (support@whofi.com) gives each library its address.
- **Plan: a live second tool, not the index.** Add a `get_upcoming_events` tool that reads the feed live (keeping a copy for about an hour), filters to upcoming events, and gives the model the whole upcoming list (about 1,700 words for a month, so no search needed). The tool's description tells the agent to use it for programs, classes, storytimes, and events; `search_documents` handles everything else. Then remove the snapshot.
- **Data note:** the ESL listing says 3:00–4:00 pm, but its description says "every Tuesday evening at 7pm." Fix in WhoFi.
- **Proposal fit:** events are "local information" (Q22). No divergence.

## Current setup

| Piece | What we use | Open? |
|---|---|---|
| Chat model | `openai/gpt-oss-120b` via Groq (free tier) | Open-weight (Apache 2.0). Meets proposal Q20. |
| Embeddings (search) | `BAAI/bge-small-en-v1.5` | Open (MIT) |
| Keyword search | BM25 (`llama-index-retrievers-bm25`, bm25s, PyStemmer) | Open source |
| Collections | One per folder in `data/`: `official/` (123 chunks) and `meetings/` (1,078), searched by separate tools | (design) |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Open (Apache 2.0) |
| Framework | LlamaIndex | Open source (MIT) |
| Web import | trafilatura (main content) + html2text (listing pages) | Open source (Apache 2.0 / GPL 3.0) |
| Interface | Streamlit | Open source (Apache 2.0) |
| Hosting | Streamlit Community Cloud | Free hosted service |
| Workspace | GitHub Codespaces (default setup) | Free monthly hours |

Ready but switched off: **OLMo 3.1 32B Instruct** (Ai2, fully open: weights, training data, and code) via OpenRouter. It turns on automatically when an `openrouter_api` secret is added in Streamlit, and switches off when the secret is removed.

## How the pieces fit

- **Source references.** Each answer ends with a "Sources:" list. `friendly_source()` in `app.py` turns file names into readable labels:
  - Files listed in `sources.json` show their title and web address.
  - Meeting videos show the meeting name and a YouTube link.
  - PDFs show the document name and page number.
  - Anything else shows its file name without the extension, so name new files descriptively.
- **`sources.json`** is the "card catalog" of titles and web addresses. `webimport.py` updates it automatically each time it runs, keeping entries added by hand (like the FAQ). It sits outside `data/` so it isn't indexed as a document. The app falls back to plain file names if the file is missing or has a JSON error.
- **Web import.** `webimport.py` downloads each page in its URL list. Normal pages: trafilatura keeps the main content and drops menus and footers. Pages on `WHOLE_PAGE_URLS` (listing pages like the calendar): saved whole with html2text. Saves `data/web_N.txt` (numbered by list position, so add new URLs at the end) and records title and address in `sources.json`. If a page can't be downloaded or has no content, it keeps the old copy and says so.
- **Chunking.** `build_index.py` cuts at headings first, then splits long sections to ~512 tokens. Settings live in `search.py`, shared with the app.
- **Search (`search.py`).** Meaning search and keyword search each find 20 candidates; the lists are merged (Reciprocal Rank Fusion); the reranker scores them; passages scoring at least −7.0 go to the model, up to 5.
- **Today's date.** `ask_agent` sends a separate system note ("Today is …", Central time) with every question. It isn't in the main prompt because the prompt is built once at startup.
- **Dollar signs.** Answers are escaped (`$` → `\$`) before display, because Streamlit treats text between two `$` signs as math.
- **"Not found" isn't "no."** Not-found answers start with "I couldn't find anything about [topic] in our documents," suggest asking staff, and never imply "no" or reason from what a list leaves out. The prompt includes a worked example. Past events are marked as passed.
- **Gap log.** When an answer contains "couldn't find anything," `log_gap()` posts the question and time (nothing else) as a comment on GitHub Issue #1. It skips quietly if the secrets are missing or GitHub is unreachable.
- **"How I found this."** Under each answer, an expandable panel shows the agent's actual search query and the passages it received.
- **`check_search.py`** shows what the search finds for each test question (scores, which search found it, whether it was handed to the model), without calling the AI model. `python check_search.py "your question"` tests one question. It needs the embedding and reranker models, so run it in Codespaces.
- **Building the index.** `build_index.py` updates `storage/` from `data/`, processing only new, changed, moved, or removed documents; it keeps each file's fingerprint in `storage/build_manifest.json` (`--full` rebuilds everything). Its embedding model and chunk settings come from `search.py`. Build in Codespaces and commit `storage/`, rather than letting Streamlit rebuild on every restart.
- **Adding documents (routine):** put files in the right folder of `data/` (`official/` or `meetings/`) (or run an import script) → `python build_index.py` → commit and push `data`, `sources.json`, and `storage`.
- **Codespaces.** No custom setup file (`.devcontainer` was removed again Nov 3 after it reappeared), so GitHub uses its default image, which starts quickly. Install: `pip install torch --index-url https://download.pytorch.org/whl/cpu`, then `pip install -r requirements.txt`. Stop the codespace when done.
- **Git habit.** Run `git pull` before starting work in Codespaces and again before pushing. If a push is rejected as "behind," run `git pull --rebase`, then `git push`.
- **Secrets (Streamlit → Settings → Secrets):** `groq_api`; optional `openrouter_api` and `llm_model`; for the gap log, `github_token` (fine-grained, Issues read/write on this repo only; renew before it expires) and `gap_issue_number`.

## Checking against the Humanity AI proposal

### Already meets the proposal
- **Open models only (Q20).** The proposal says "open-weight and/or open-source models only." gpt-oss-120b is open-weight, so we comply. OLMo would go further (fully open), but the proposal doesn't require that. The embedding model and reranker are open models too.
- **Uses local information (Q22).** The app searches meeting minutes, library policy, library and city web pages, a staff FAQ, and (temporarily) a snapshot of the events calendar.
- **Residents can check accuracy (Q23).** Answers cite their sources with links, and "How I found this" shows exactly what the assistant searched for and read. Sticking to official, public, citable sources (including a public staff FAQ) keeps that true.
- **Input → action → feedback, in miniature (Q22).** Patron questions → gap log/FAQ counts → content added or a case made to the website team.
- **Built from open-source parts that other libraries can reuse** (Q22: "an open-source tool available to other libraries"). General tools (trafilatura, heading-aware chunking, hybrid search) rather than rules tuned to North Liberty's website template; documented in the Implementation Guide.
- **Partnership with local leaders (Q22/Q23).** Working with the city clerk's office on meeting data access (CivicClerk) is an early example of the city partnership the proposal relies on.

### Where we differ (and how to close the gap)
1. **The code isn't legally open source yet.** The repo is public but has no license file. *Fix:* add an open-source license once ownership is confirmed (see License notes below).
2. **It's built for one library.** "North Liberty" is written into the code and prompt. The proposal says each community owns its own tool. *Fix:* settings file. Planned for a future phase.
3. **It answers questions; the proposal's tool makes sense of resident input.** The proposal's tool reports themes in residents' responses (audio transcripts, Pol.is), combines them with local information, produces a report for the council, and shows residents how their input was used. The current app only answers questions about documents. This is the biggest gap, and it's expected at the prototype stage. Jigsaw's Sensemaker (below) is a candidate for the theming part.
4. **No feedback loop yet.** There's no way yet to record the council's response or show residents how their input was used.

### Things to consider (not differences)
- **Questions go to a commercial host (Groq).** The proposal doesn't forbid this, but once the tool handles resident input, privacy matters more. Options: a public-interest host such as Public AI, or the offline setup below.
- **Free-tier cap.** About 8,000 tokens per minute, roughly one question a minute. Fine for testing, not for ten communities.
- **Resident input and patron questions must stay out of the public repo.** See Privacy above.
- **Ready to share broadly?** Library content is public record and the code is meant to be open, so access isn't a concern. The real question is whether it's tested enough.
- **Other communities will use different vendor platforms** (meeting portals, event calendars). The packaged tool should make it easy to plug in whatever official feeds each community has.

## Sensemaker (Jigsaw) — candidate for the theming step

Checked Nov 2, 2026 ([repo](https://github.com/Jigsaw-Code/sensemaking-tools)).

- **What it does:** a command-line pipeline that turns a pile of free-text responses into topics, representative quotes, summaries, and an interactive report. This matches the proposal's "report themes and connections in responses" (Q22).
- **It's a separate tool, not part of the chat app.** It runs as a batch job (input file in, report out), e.g., in Codespaces.
- **Input:** a CSV with two columns, `participant_id` and `survey_text`. Audio transcripts and Pol.is comments would each need converting to that shape. The current version doesn't use Pol.is agree/disagree votes.
- **Needs:** Python 3, plus Node.js for the interactive report step.
- **License:** Apache 2.0, compatible with our plans.
- **Not actively maintained.** Jigsaw offers it as a reference and starting point, not a supported product.

**⚠️ Divergence risk:** Sensemaker uses **Google Gemini by default, which is not open-weight**. Using the default would break proposal Q20. To stay compliant, it must be pointed at an open-weight model through its "OpenAI API compatible" setting, for example gpt-oss-120b on Groq:
- `MODEL_ENDPOINT_TYPE=openai_api_compatible`
- `OPENAI_API_ENDPOINT_URL=https://api.groq.com/openai/v1`
- `OPENAI_API_ENDPOINT_KEY=<Groq key>`
- `--model_name openai/gpt-oss-120b`

Skip the optional moderation step, which uses Google Cloud.

**Cautions:**
- Jigsaw notes open models may struggle with the most complex steps (e.g., "Simulated Juries"). Start with topic discovery only.
- Groq's free-tier cap is far below Sensemaker's default of 20 calls at once. Lower it with `-c 1` or `-c 2`.
- Test with sample or public data first, not real resident input.

## License notes

- **Who owns the code?** Code written as part of a library job may belong to the library or city rather than to Nick. Confirm with a supervisor (or the city) before adding a license.
- **The license covers the code, not the documents.** The `data/` folder (meeting transcripts, policy manual, web pages, staff FAQ) and the `storage/` index keep their own terms. State this in the README.
- **Hard to take back.** Once code is released under an open license, copies already out there keep that license.
- **Dependencies are compatible** with an MIT or Apache 2.0 license for the code. Note: `html2text` (import script only) is GPL 3.0 and PyMuPDF is AGPL/commercial dual-licensed; check whether that matters for how the package is distributed.
- **Choice:** MIT (simplest) or Apache 2.0 (adds patent protection). Check whether ARSL or the funder has a preference.

## Future need: offline version

**Goal:** an assistant that works with no internet connection, so no data leaves the building.

**What it would take:**
- **Run the app on a local machine** instead of Streamlit Cloud.
- **Serve the model locally** with Ollama, using an open model such as OLMo.
- **Search already works offline.** The embedding model, reranker, documents, and index are all stored with the app (models download once, then are cached).
- **Code change is small:** add Ollama as a third model option, switched on the same way as OpenRouter.

**The real obstacle is hardware.** On Nick's computer each answer took 20–40 seconds. A usable setup needs a machine with a decent graphics card or an Apple Silicon Mac.

**Proposal angle:** small and rural libraries often have limited budgets and connectivity, so an offline option on modest library hardware fits the proposal's audience well.

**Lesson from earlier testing:** small models struggle with tool calling. Test any local model's ability to call the search tool before choosing it.

## Decisions log

- **Oct 30, 2026:** Left Lightning AI. GitHub now holds the code and Streamlit Cloud runs the app. Repo flattened and SSH key removed.
- **Oct 30, 2026:** Fixed two deployment bugs: the secret was misspelled, and the agent had no running event loop. App is working.
- **Oct 30, 2026:** Added the OLMo/OpenRouter option, and the app now shows the active model on screen.
- **Oct 30, 2026:** Decided to keep Groq (gpt-oss-120b) for now. It meets the proposal's open-weight requirement. Offline use is a future goal.
- **Oct 30, 2026:** Set the roadmap: Nick tests alone first, then library staff (milestone 1). Making it copyable for other libraries is a future phase. Resident input will come from audio transcripts and Pol.is.
- **Oct 30, 2026:** Nick added source references to answers (the `friendly_source` helper).
- **Oct 30, 2026:** Codespaces kept freezing while downloading custom setup images. Removed the repo's setup folder so GitHub uses its default image.
- **Nov 2, 2026:** `webimport.py` now records each page's title and web address in `sources.json` automatically. First catalog created.
- **Nov 2, 2026:** Looked into Jigsaw's Sensemaker for the theming step. Must be configured for an open-weight model (not its Gemini default) to meet Q20.
- **Nov 2, 2026:** Added `build_index.py` so the index is built in Codespaces and committed, instead of rebuilt by Streamlit on every restart.
- **Nov 2, 2026:** WhoFi calendar page can't be imported (built with JavaScript; crawling discouraged). Plan: read WhoFi's RSS feed live through a second agent tool. RSS needs approval, so the events tool is on the future list; no temporary version.
- **Nov 2, 2026:** Keeping gpt-oss-120b for now. Model comparison planned for after the search fix, using the test set.
- **Nov 2, 2026:** Baseline test run of Nick's 10 questions: 3 ✅, 5 ⚠️, 2 ❌. Quick fixes (dollar signs, today's date, "not found isn't no") brought it to 6 ✅, 3 ⚠️, 1 ❌.
- **Nov 2, 2026:** Gap log added: unanswered questions go to GitHub Issue #1 (question, date, time only).
- **Nov 2, 2026:** Project principle set: avoid temporary fixes; wait for a good one.
- **Nov 2, 2026:** Decided on a staff-maintained Library Services FAQ (public, citable on GitHub), plus counting how often answers use it, as data for the website team.
- **Nov 3, 2026:** Catalog fallback fixed; FAQ indexed; stronger "not found" wording applied; `.devcontainer` removed again; `check_search.py` added. Measured search scores: a cutoff alone won't work, and website menus polluted results.
- **Nov 3, 2026:** For cleaning web pages, chose trafilatura (general, works on any site, open source) over a hand-written rule tuned to the library/city site template.
- **Nov 4, 2026:** Project goal added: package for other communities; started the Implementation Guide.
- **Nov 4, 2026:** trafilatura dropped calendar event titles; added `WHOLE_PAGE_URLS` so listing pages are saved whole. Considered an automatic "kept %" flag; not needed for now.
- **Nov 4, 2026:** Tested two rerankers: bge-reranker-base judged best but ~28 s per question (too slow); MiniLM fast but less accurate. Decision deferred. Tested keyword (BM25) search: found passages meaning search missed.
- **Nov 4, 2026:** Plan revised: heading-aware chunks → hybrid search → reranker decision → app search rewrite → embedding upgrade experiment. Chosen because these fixes are model-independent and carry over to other libraries' setups.
- **Nov 4, 2026:** Heading-aware chunking tested by Nick: trustees chunk now #2 for "Who is on the library board?" "Next board meeting" judged a source problem (no official calendar of upcoming meeting dates), not a search problem.
- **Nov 4, 2026:** City meetings are published through a CivicClerk portal (JavaScript app; undocumented data feed). Nick subscribed to its notifications to look for usable links; otherwise parked alongside the WhoFi RSS item, pending an official feed or permission from the city clerk's office.
- **Nov 4, 2026:** Merged PR #2 (hybrid search, MiniLM reranker with a −7.0 cutoff, passages handed to the model with source labels) and PR #3 ("How I found this" panel). Nick fixed the date rule in the prompt.
- **Nov 4, 2026:** Full baseline, 2 runs each: 5 ✅, 3 ⚠️, 2 ❌, with the same score on both runs for every question. Q1 gave a confident wrong date from another board's transcript. Proposed next: staff FAQ changes, then separating meeting transcripts from official documents (revised Nov 10).
- **Nov 10, 2026:** Nick's rule: the staff FAQ holds only information that exists nowhere else (notary). Fax and study rooms stay with their official documents, so they're always answered from the maintained source. Q4 becomes a search fix (separate transcripts, source line); Q8 becomes a source fix (fax is mentioned only inside the Proctoring policy).
- **Nov 13, 2026:** Found that the assistant rewrites each question into its own search query and pads it ("notary services North Liberty Library"). The reranker then favors passages full of the library's name, so the FAQ dropped out of the top 10 and every score turned positive (breaking the not-found cutoff). Fixed with the search tool's description: short queries from the key words; keep department and board names; never add "North Liberty." Notary now answered correctly. If the instruction doesn't hold, a backstop in `search.py` would strip the place name (a settings-file entry for other libraries).
- **Nov 13, 2026:** The December 2025 policy manual said four reservations (p. 20, item K); the Room Reservations page said "four (3)." Nick fixed the page and uploaded the November 2026 manual, which says three and adds one reservation per day. Kept as PDF (not Word) so citations keep page numbers.
- **Nov 13, 2026:** Added a driver's license FAQ entry ("No, the kiosk is gone") for a commonly asked, discontinued service with no official page.
- **Nov 13, 2026:** Prompt line added: no citation marks in the answer; the "Sources:" list is the only citation. Confirmed working.
- **Nov 13, 2026:** Nick's rule: when it's unclear which department a question is about, the assistant should ask. Planned after department labels and conversation memory.
- **Nov 13, 2026:** Found the app doesn't reload an index-only push (cached in memory). Fix planned; reboot the app after rebuilds until then.
- **Nov 16, 2026:** Merged PR #4: two collections, "official" and "meetings" (by the `video_` file prefix), each with its own search tool; no rebuild needed. Codespaces check: "library board meeting" put the trustees chunk ("usually meets the third Monday") at #1, with no transcripts. Pool questions routed to meeting records; notary, printing, study rooms unchanged. Also merged: automatic reload when a new index is pushed.
- **Nov 16, 2026:** The assistant then searched "board meeting schedule", dropping "library", and found nothing (the "don't add words" rule made it strip a word that mattered). Fixed by adding example queries to both tool descriptions ("When does the library board meet?" → "library board meeting"). Examples steer the model more reliably than rules. Nick corrected the stated reason: not every document names the town; the point is that the town's name doesn't narrow anything.
- **Nov 16, 2026:** Nick raised community history (from before the town was named North Liberty). Plan: its own collection whose search keeps place names, plus a place-names reference document. Added to future tasks.
- **Nov 17, 2026:** Merged interface styling (PR #6: theme file with light and dark colors at WCAG AA contrast, welcome screen, example questions; requires Streamlit 1.67+).
- **Nov 17, 2026:** Rebuilt with the source line. Not-found questions score about −11 (cutoff −7); notary 8.63 with the next passage at −10.13. Side effect found: policy manual chunks labeled "Library" twice outranked the trustees section (labeled "City of North Liberty"), which fell to #5 for "library board meeting." Fixed with section-level departments (PR #7): a section whose heading names a board gets that board as its department. Trustees section back to #2; "parks commission" #1 at 7.03.
- **Nov 17, 2026:** Planned the document "front door": folders as collections and incremental builds, one import script with an inbox, automatic builds with GitHub Actions (warnings and a build report, no automatic moving), then converters and the settings file. Nick: the import script should handle placement for the librarian.
- **Nov 17, 2026:** Building and testing moves to Claude Code in the Codespace; planning stays in the claude.ai Project. Project docs copied into the repo's `docs/` folder.
- **Nov 17, 2026:** Front door step 1 built (branch `folder-collections`). Each folder in `data/` is a collection (`official/`, `meetings/`); the `video_` file-name rule is gone (the prefix still gives YouTube links). `build_index.py` keeps a fingerprint of each document (its contents plus its folder, title, and department) in `storage/build_manifest.json` and processes only what changed; a change to the embedding model, chunk sizes, or department rules rebuilds everything on its own. Tested on Windows: full build 1,201 chunks in about 3.5 minutes; an FAQ edit, a move between folders, and a removal each took about 20 seconds (mostly loading the models), and `check_search.py` results were identical to the old index for every test question in both collections. Found along the way: on Windows the file reader kept Windows line breaks in the text, which changed 126 chunks; the build now reads every file with plain line breaks, so Windows and the Codespace build the same index. The app still has two hand-written search tools; a third collection (city code) gets its tool and description when it arrives in step 2. Old scripts `moredecai.py` and `tests.py` still read `data/` directly and no longer work; candidates for removal.

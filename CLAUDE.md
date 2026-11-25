# Library & City Info Assistant (MordecAI)

A RAG assistant for small public libraries
 
## Read these first

- `docs/project-notes.md`: the plan ("Next up"), decisions waiting on Nick, decisions log, source rules, privacy
- `docs/test-questions.md`: the test set and every round's results
- `docs/implementation-guide.md`: how another library would set this up

## Project 
- Initially a RAG that answers questions about library and city operations from the library's and city's own documents, with citations. 
- Future iterations will include local history documents and public input largely via Pol.is polls
- Initial development for the North Liberty Library in North Liberty.  A prototype for the Humanity AI open call proposal.

## Structure

- **This is a learning project.** Explain each change simply: what it does and why. For small edits, show the exact before/after lines. Pause before committing or pushing.
- **Avoid temporary fixes.** Wait for a good, lasting fix rather than patching around a problem. If a problem is really a missing or wrong source, fix it at the source.
- **Follow the Humanity AI proposal** (open-weight models only, local information, residents can check answers). Note any divergence in `docs/project-notes.md`.
- **Package for other libraries.** Prefer general tools over rules tuned to North Liberty; record how-tos and every package used in `docs/implementation-guide.md`.
- **Keep the docs current.** After each change or test round, update the decisions log, "Next up," and the test results.
- **One change at a time**, tested before the next.
- Larger changes go on a branch with a pull request for Nick to review and merge.

## Testing a change

1. `python check_search.py "short query"`: what the search finds, with scores (no AI cost). Test with the *assistant's* short query (the "Searched for" line in the app), not just the full question. `--meetings` searches transcripts; `--all` searches everything together.
2. In the app, ask each test question 2–3 times; open "How I found this" for any miss.
3. Not-found questions (telescope, passport photos) must stay below the −7.0 cutoff.

Changes to `data/`, `sources.py`, `sources.json`, or `build_index.py` need `python build_index.py`, then commit and push `storage/`. Changes to `app.py` or `search.py` don't. The app reloads a new index on its own.

## Rules that don't bend

- **Never commit secrets.** API keys and tokens live only in Streamlit secrets (`groq_api`, `openrouter_api`, `github_token`, `gap_issue_number`).
- **Patron privacy:** logs record only the question, date, and time. Nothing identifying who asked (Iowa Code §22.7(13)).
- **Sources:** official, public, citable, maintained. No social media. Respect robots.txt and vendor terms; don't build on undocumented vendor feeds without permission. The staff FAQ holds only information published nowhere else.
- **Models:** open-weight only (proposal Q20).

## Map

| File | What it is |
|---|---|
| `app.py` | Streamlit chat app: prompt, search tools, "How I found this" |
| `search.py` | All search settings: models, chunking, collections, hybrid search, reranker cutoff |
| `sources.py` | Titles, links, and departments (the source line on every chunk) |
| `sources.json` | The catalog: title, web address, department per file |
| `build_index.py` | Updates `storage/` from `data/`: only new, changed, or removed documents (`--full` for everything) |
| `check_search.py` | Search diagnostics |
| `intake.py` | Files documents from `inbox/` (files, `links.txt`) into `data/` collections and `sources.json`; report in `inbox/REPORT.md`. `--refresh` re-downloads web pages. Needs `requirements-intake.txt`. |
| `city_code.py` | Splits a code of ordinances into one file per chapter, one heading per section (used by `intake.py`) |
| `data/` | Documents. Each folder is a collection with its own search tool (`official/`, `meetings/`, `city_code/`). `storage/` is the built index (commit it), with `build_manifest.json` (each document's fingerprint and chunk count). |

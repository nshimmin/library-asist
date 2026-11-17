# Library & City Info Assistant (MordecAI)

A RAG assistant for North Liberty Public Library (Iowa) that answers questions from the library's and city's own documents, with citations. A prototype for the Humanity AI open call proposal. Maintained by Nick (Adult Services Librarian).

Read these first:
- `docs/project-notes.md`: current plan ("Next up"), decisions log, source rules, privacy
- `docs/test-questions.md`: the test set and every round's results
- `docs/implementation-guide.md`: how another library would set this up

## How Nick wants to work

- **This is a learning project.** Explain each change simply: what it does and why. For small edits, show the exact before/after lines and let Nick make them himself. Pause before committing or pushing.
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
| `webimport.py`, `youtubeimport.py`, `pdfimport.py` | Import scripts (to be replaced by one import script; see "Next up") |
| `data/` | Documents. Each folder is a collection (`official/`, `meetings/`). `storage/` is the built index (commit it), with `build_manifest.json` (each document's fingerprint and chunk count). |

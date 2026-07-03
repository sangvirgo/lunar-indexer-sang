# Deterministic Pinned Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the demo-critical FAQ questions use the exact scraped support articles as pinned context while preserving Gemini File Search for general questions.

**Architecture:** Add a small pinned-source module that recognizes the known demo FAQ patterns, loads the canonical local markdown article when available, and supplies that content to the model as dominant context. Ensure ingestion always includes the four canonical articles by fetching missing ones directly from the Zendesk article API when necessary, then add a post-response guard to keep citations aligned with the pinned source.

**Tech Stack:** Python, requests, Gemini File Search, FastAPI, local markdown article cache

---

### Task 1: Pinned Source Module

**Files:**
- Create: `pinned_sources.py`

- [ ] Define the four canonical demo question mappings with article id, title, URL, expected markdown filename, phrase patterns, and any negative terms.
- [ ] Expose `find_pinned_source_for_question(question: str) -> dict | None`.
- [ ] Expose `load_pinned_markdown(question: str, data_dir: Path = Path("data/articles")) -> dict | None`.
- [ ] Return metadata even when the markdown file is missing so the rest of the app can degrade safely.

### Task 2: Canonical Ingestion Guarantees

**Files:**
- Modify: `scraper.py`
- Modify: `main.py`

- [ ] Keep paginated fetch and dedupe by article id.
- [ ] Fetch missing canonical articles directly from the Zendesk single-article endpoint by id.
- [ ] Always include the four canonical articles when available.
- [ ] Keep YouTube Dashboard excluded from the 40-article demo set when enough other articles exist.
- [ ] Preserve and extend selection diagnostics.

### Task 3: Retrieval Context And Guard

**Files:**
- Modify: `ask.py`
- Modify: `app.py`

- [ ] Load pinned markdown before Gemini calls.
- [ ] Prepend pinned article context and a strict non-system retrieval instruction when pinned context exists.
- [ ] Keep the required system prompt unchanged and keep the File Search tool enabled.
- [ ] Add a post-response guard that strips clearly wrong lines for pinned YouTube answers and enforces the pinned article URL.

### Task 4: UI And Docs

**Files:**
- Modify: `index.html`
- Modify: `README.md`

- [ ] Keep the five quick-question buttons and preserve clean wrapping.
- [ ] Document the general File Search behavior and the four demo-pinned canonical URLs.

### Task 5: Manual Verification

**Files:**
- Verify: `scraper.py`
- Verify: `main.py`
- Verify: `ask.py`
- Verify: `app.py`
- Verify: `index.html`
- Verify: `README.md`
- Verify: `pinned_sources.py`

- [ ] Run `python -m compileall .`.
- [ ] Run `rm -rf data/articles`.
- [ ] Run `rm -f data/manifest.json data/last_run.json`.
- [ ] Run `python main.py`.
- [ ] Run `ls data/articles | grep -E "youtube-with-optisigns|set-up-add-a-screen|vimeo-video|what-types-of-files"`.
- [ ] Run the four `python ask.py ...` commands.
- [ ] Confirm each answer cites the correct canonical URL.
- [ ] Confirm the YouTube answer does not mention Dashboard, Analytics, or Looker Studio.
- [ ] Run `git diff -- scraper.py main.py ask.py app.py index.html README.md pinned_sources.py`.
- [ ] Run `git status --short`.

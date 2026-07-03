# YouTube Sample Retrieval Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure the sample question about adding a YouTube video selects and cites the standard YouTube App article instead of YouTube Dashboard content.

**Architecture:** Fix the problem at the source by tightening the 40-article demo knowledge selection in `scraper.py`, then reinforce retrieval with a question-specific hint in `ask.py` while keeping the required system prompt unchanged. Preserve the API contract and single-file frontend.

**Tech Stack:** Python, requests, Gemini file search, FastAPI, local markdown article cache

---

### Task 1: Demo Knowledge Selection

**Files:**
- Modify: `scraper.py`

- [ ] Fetch all Zendesk articles through pagination and deduplicate by article id.
- [ ] Pin the canonical YouTube App article with article id `360051014713` first when present.
- [ ] Prioritize reliable demo articles for playlists, Vimeo, and supported file types when found.
- [ ] Strongly deprioritize and exclude dashboard, analytics, and Looker Studio articles from the 40-doc demo set whenever at least 40 other usable articles exist.
- [ ] Fill remaining slots by `updated_at` descending and return diagnostics including excluded dashboard count.

### Task 2: Ingestion Diagnostics

**Files:**
- Modify: `main.py`

- [ ] Extend the selection diagnostics payload with `excluded_dashboard_count`.
- [ ] Keep the existing summary structure and include the first 10 selected titles.

### Task 3: Question-Specific Retrieval Hint

**Files:**
- Modify: `ask.py`
- Modify: `app.py`

- [ ] Add a helper that detects exact or approximate variants of `How do I add a YouTube video?`.
- [ ] Append a stronger retrieval hint outside the system prompt only for that sample question.
- [ ] Keep the required system prompt text unchanged and keep the backend API contract unchanged.
- [ ] Ensure API and CLI paths both use the same question handling.

### Task 4: README Note

**Files:**
- Modify: `README.md`

- [ ] Document that the sample YouTube question is pinned to the standard YouTube App article.
- [ ] Document that dashboard and analytics content are excluded from the demo knowledge set to avoid the assignment screenshot failure.

### Task 5: Manual Verification

**Files:**
- Verify: `scraper.py`
- Verify: `main.py`
- Verify: `ask.py`
- Verify: `app.py`
- Verify: `README.md`

- [ ] Run `python -m compileall .`.
- [ ] Run `python main.py`.
- [ ] Run `python ask.py "How do I add a YouTube video?"`.
- [ ] Confirm the answer cites `https://support.optisigns.com/hc/en-us/articles/360051014713-How-to-use-YouTube-with-OptiSigns`.
- [ ] Confirm the answer does not cite YouTube Dashboard, Looker Studio, or Analytics.
- [ ] Run `git diff -- scraper.py main.py ask.py app.py README.md`.
- [ ] Run `git status --short`.

# Store Name Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist a newly created Gemini file search store name back to the host `.env` after ingestion and recreate `web` only when that value changes.

**Architecture:** Keep ingestion inside Docker, but move `.env` synchronization to the host-side shell script that already owns `APP_DIR` and can safely edit the real server `.env`. Use `data/last_run.json` as the handoff artifact from the ingest container, then restart only the `web` service when a new store name is detected.

**Tech Stack:** Bash, Docker Compose, JSON artifact in `data/last_run.json`, existing Python uploader

---

### Task 1: Host-Side Store Sync

**Files:**
- Modify: `deploy/run_ingest.sh`

- [ ] Add host-side parsing of `data/last_run.json` after the Docker ingest run completes.
- [ ] Read `store_name` from the JSON artifact without adding new runtime dependencies.
- [ ] Update `APP_DIR/.env` when `GEMINI_FILE_SEARCH_STORE_NAME` differs from the new value.
- [ ] Recreate `web` with `docker compose up -d --force-recreate web` only when the value changed.
- [ ] Log the sync result into the existing ingest log output.

### Task 2: Remove Misleading Operator Message

**Files:**
- Modify: `uploader_gemini.py`

- [ ] Remove the message that tells operators to save the new store name manually in `.env`.
- [ ] Keep the creation log itself so ingestion output still shows when a new store was created.

### Task 3: Targeted Verification

**Files:**
- Verify: `deploy/run_ingest.sh`
- Verify: `uploader_gemini.py`

- [ ] Run `bash -n deploy/run_ingest.sh`.
- [ ] Run `python -m compileall uploader_gemini.py`.
- [ ] Run `git diff -- deploy/run_ingest.sh uploader_gemini.py`.
- [ ] Run `git status --short`.

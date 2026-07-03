# Project Setup

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env
python main.py
python ask.py "What is indexed?"
uvicorn app:app --reload
```

## Docker Run

```bash
docker build -t rag-demo-local .
docker run --rm --env-file .env rag-demo-local
docker compose up -d web
docker compose ps
docker compose logs --tail=80 web
docker compose --profile job run --rm ingest
docker compose down
```

## CI/CD And Scheduled Ingestion

Public demo URL: http://159.223.93.125

For deterministic demo knowledge, the generated Markdown snapshot under `data/articles/*.md` is committed to Git and deployed with the app. This keeps local `ask.py` results and deployed server knowledge aligned to the same source files.

`data/manifest.json` and `data/last_run.json` are runtime artifacts. They are not committed and should be treated as disposable ingestion state on each environment.

GitHub Actions force-syncs source code and committed Markdown knowledge files to DigitalOcean with `rsync --delete`, rebuilds Docker on the server, restarts the web container, installs or updates the cron job, and runs ingestion once after deploy. The workflow triggers on pushes to `main` and `workflow_dispatch`. The server `.env` must already exist manually before deploy and is never overwritten by the workflow.

The app uses Gemini File Search for general questions. For a few demo-critical FAQ questions, it also pins the exact scraped support article as additional context to avoid ambiguous retrieval. This is not answer hard-coding; answers are still generated from scraped docs.

The ingestion job always includes these canonical demo articles when available, then fills the remaining slots with the latest updated help-center articles up to `ARTICLE_LIMIT=40`:
- https://support.optisigns.com/hc/en-us/articles/360051014713-How-to-use-YouTube-with-OptiSigns
- https://support.optisigns.com/hc/en-us/articles/360016374813-Set-up-add-a-screen
- https://support.optisigns.com/hc/en-us/articles/360016254994-How-to-add-use-Vimeo-video-with-OptiSigns
- https://support.optisigns.com/hc/en-us/articles/360016342373-What-types-of-files-are-supported

Dashboard and analytics articles are excluded from the demo knowledge set when there are enough other usable articles, so the required assignment screenshot uses the standard YouTube App article instead of YouTube Dashboard or Looker Studio content.

Scheduled ingestion runs every 2 hours with cron expression `0 */2 * * *`. The recurring schedule is installed into the deploy user crontab on the server.

The ingestion log file is `/var/log/lunar-indexer/ingest.log`, and the last run artifact is `data/last_run.json`.

Manual force-refresh commands:

```bash
cd /opt/lunar-indexer
git pull origin main
rm -f data/manifest.json data/last_run.json
sed -i 's|^GEMINI_FILE_SEARCH_STORE_NAME=.*|GEMINI_FILE_SEARCH_STORE_NAME=|' .env
APP_DIR=/opt/lunar-indexer ./deploy/run_ingest.sh
NEW_STORE=$(grep -o 'fileSearchStores/[A-Za-z0-9_-]*' /var/log/lunar-indexer/ingest.log | tail -1)
sed -i "s|^GEMINI_FILE_SEARCH_STORE_NAME=.*|GEMINI_FILE_SEARCH_STORE_NAME=$NEW_STORE|" .env
docker compose up -d --build --force-recreate web
docker compose run --rm web python ask.py "How do I add a YouTube video?"
```

## Screenshot

Current UI/demo references:

- Gemini upload flow screenshot: `image.png`
- Question and response screenshot: `image-1.png`

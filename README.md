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

GitHub Actions force-syncs source code to DigitalOcean with `rsync --delete`, rebuilds Docker on the server, restarts the web container, installs or updates the cron job, and runs ingestion once after deploy. The workflow triggers on pushes to `main` and `workflow_dispatch`. The server `.env` must already exist manually before deploy and is never overwritten by the workflow.

The ingestion job prioritizes YouTube and video related articles for the required sample question, then fills the remaining slots with the latest updated help-center articles up to `ARTICLE_LIMIT=40`.

Scheduled ingestion runs every 2 hours with cron expression `0 */2 * * *`. The recurring schedule is installed into the deploy user crontab on the server.

The ingestion log file is `/var/log/lunar-indexer/ingest.log`, and the last run artifact is `data/last_run.json`.

Manual server commands:

```bash
cd /opt/lunar-indexer
APP_DIR=/opt/lunar-indexer ./deploy/run_ingest.sh
tail -n 100 /var/log/lunar-indexer/ingest.log
cat data/last_run.json
docker compose ps
```

## Screenshot

Current UI/demo references:

- Gemini upload flow screenshot: `image.png`
- Question and response screenshot: `image-1.png`

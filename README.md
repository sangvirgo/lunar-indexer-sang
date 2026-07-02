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

GitHub Actions deploys source code to DigitalOcean by `rsync`, and the server builds Docker locally after each push to `main` or manual `workflow_dispatch`. The server `.env` must already exist manually before deploy and is never overwritten by the workflow.

Public demo URL: http://159.223.93.125

Scheduled ingestion runs daily at `01:00`, `07:00`, `13:00`, and `19:00` with cron expression `0 1-23/6 * * *`. The recurring schedule is installed into the deploy user crontab on the server.

The ingestion log file is `/var/log/lunar-indexer/ingest.log`, and the last run artifact is `data/last_run.json`.

Verification commands:

```bash
crontab -l
tail -n 100 /var/log/lunar-indexer/ingest.log
cat data/last_run.json
docker compose ps
docker compose logs --tail=100 web
```

## Screenshot

Current UI/demo references:

- Gemini upload flow screenshot: `image.png`
- Question and response screenshot: `image-1.png`

# Project Setup

Setup placeholder.

## Local Run

Local run placeholder.

Manual verification commands:

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

Docker run placeholder.

```bash
docker build -t rag-demo-local .
docker run --rm --env-file .env rag-demo-local
docker compose up -d web
docker compose ps
docker compose logs --tail=80 web
docker compose --profile job run --rm ingest
docker compose down
```

## DigitalOcean Deploy

DigitalOcean deploy placeholder.

## Daily Job Logs

Daily job logs placeholder.

## Screenshot

Screenshot placeholder.

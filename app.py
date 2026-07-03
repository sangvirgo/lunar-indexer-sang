from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ask import format_answer, ask_question
from pinned_sources import load_pinned_markdown


PROJECT_ROOT = Path(__file__).resolve().parent
INDEX_HTML = PROJECT_ROOT / "index.html"

app = FastAPI(title="OptiBot Chat Demo")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    answer: str


def _require_env(name: str, message: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise HTTPException(status_code=500, detail=message)
    return value


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(INDEX_HTML)


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    load_dotenv()

    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message must not be empty.")

    _require_env("GEMINI_API_KEY", "Missing GEMINI_API_KEY. Add it to .env.")
    _require_env(
        "GEMINI_FILE_SEARCH_STORE_NAME",
        "Missing GEMINI_FILE_SEARCH_STORE_NAME. Add it to .env.",
    )

    pinned_source = load_pinned_markdown(message, PROJECT_ROOT / "data" / "articles")

    try:
        response = ask_question(message, pinned_source=pinned_source)
        answer, _ = format_answer(response, message, pinned_source=pinned_source)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Chat request failed: {exc}") from exc

    return ChatResponse(answer=answer)

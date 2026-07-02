from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from google import genai


load_dotenv()


CHUNK_MAX_TOKENS = 512
CHUNK_OVERLAP_TOKENS = 100
POLL_INTERVAL_SECONDS = 2
POLL_TIMEOUT_SECONDS = 300


@dataclass
class UploadDocument:
    article_id: int
    title: str
    path: Path
    sha256: str


@dataclass
class UploadedDocument:
    article_id: int
    path: str
    sha256: str
    document_name: str
    operation_name: str


@dataclass
class UploadResult:
    store_name: str
    uploaded_count: int
    uploaded_documents: list[UploadedDocument]
    created_store: bool


def get_gemini_settings() -> dict[str, str]:
    return {
        "api_key": os.getenv("GEMINI_API_KEY", "").strip(),
        "store_name": os.getenv("GEMINI_FILE_SEARCH_STORE_NAME", "").strip(),
    }


def require_api_key() -> str:
    api_key = get_gemini_settings()["api_key"]
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY. Add it to .env.")
    return api_key


def build_client() -> genai.Client:
    return genai.Client(api_key=require_api_key())


def _store_display_name() -> str:
    project_name = Path.cwd().name or "knowledge-base"
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return f"{project_name}-{timestamp}"


def _save_store_name_to_env(store_name: str) -> None:
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    updated = False
    new_lines: list[str] = []
    for line in lines:
        if line.startswith("GEMINI_FILE_SEARCH_STORE_NAME="):
            new_lines.append(f"GEMINI_FILE_SEARCH_STORE_NAME={store_name}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"GEMINI_FILE_SEARCH_STORE_NAME={store_name}")

    env_path.write_text("\n".join(new_lines).strip() + "\n", encoding="utf-8")
    os.environ["GEMINI_FILE_SEARCH_STORE_NAME"] = store_name


def ensure_file_search_store(client: genai.Client) -> tuple[str, bool]:
    store_name = get_gemini_settings()["store_name"]
    if store_name:
        store = client.file_search_stores.get(name=store_name)
        return store.name, False

    created_store = client.file_search_stores.create(
        config={"display_name": _store_display_name()}
    )
    created_name = created_store.name or ""
    print(f"Created Gemini File Search Store: {created_name}")
    print("Save this value in .env as GEMINI_FILE_SEARCH_STORE_NAME.")
    _save_store_name_to_env(created_name)
    return created_name, True


def _wait_for_operation(client: genai.Client, operation, timeout_seconds: int = POLL_TIMEOUT_SECONDS):
    started_at = time.monotonic()
    current = operation

    while not getattr(current, "done", False):
        if time.monotonic() - started_at > timeout_seconds:
            raise TimeoutError(
                f"Timed out waiting for upload operation {getattr(operation, 'name', '(unknown)')}"
            )
        time.sleep(POLL_INTERVAL_SECONDS)
        current = client.operations.get(current)

    if getattr(current, "error", None):
        raise RuntimeError(f"Gemini upload failed: {current.error}")

    return current


def upload_documents(
    documents: list[UploadDocument],
    *,
    client: genai.Client | None = None,
    store_name: str | None = None,
) -> UploadResult:
    client = client or build_client()
    resolved_store_name = store_name
    created_store = False
    if not resolved_store_name:
        resolved_store_name, created_store = ensure_file_search_store(client)

    uploaded_documents: list[UploadedDocument] = []
    total_documents = len(documents)
    for index, document in enumerate(documents, start=1):
        print(
            f"Uploading {index}/{total_documents}: {document.path.name}",
            flush=True,
        )
        operation = client.file_search_stores.upload_to_file_search_store(
            file_search_store_name=resolved_store_name,
            file=document.path,
            config={
                "display_name": document.title,
                "mime_type": "text/markdown",
                "chunking_config": {
                    "white_space_config": {
                        "max_tokens_per_chunk": CHUNK_MAX_TOKENS,
                        "max_overlap_tokens": CHUNK_OVERLAP_TOKENS,
                    }
                },
            },
        )
        completed = _wait_for_operation(client, operation)
        response = completed.response
        print(
            f"Uploaded {index}/{total_documents}: {document.path.name}",
            flush=True,
        )
        uploaded_documents.append(
            UploadedDocument(
                article_id=document.article_id,
                path=str(document.path),
                sha256=document.sha256,
                document_name=getattr(response, "document_name", "") if response else "",
                operation_name=getattr(completed, "name", "") or "",
            )
        )

    return UploadResult(
        store_name=resolved_store_name,
        uploaded_count=len(uploaded_documents),
        uploaded_documents=uploaded_documents,
        created_store=created_store,
    )

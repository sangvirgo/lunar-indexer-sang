from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from requests import RequestException

from markdown_cleaner import render_article_markdown
from scraper import fetch_articles
from uploader_gemini import (
    UploadDocument,
    build_client,
    ensure_file_search_store,
    upload_documents,
)


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
ARTICLES_DIR = DATA_DIR / "articles"
LAST_RUN_PATH = DATA_DIR / "last_run.json"
MANIFEST_PATH = DATA_DIR / "manifest.json"


def get_article_limit() -> int:
    raw_value = os.getenv("ARTICLE_LIMIT", "40").strip()
    return int(raw_value or "40")


def ensure_directories() -> None:
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict[str, object] | list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_manifest() -> dict[int, dict[str, object]]:
    if not MANIFEST_PATH.exists():
        return {}

    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {int(item["article_id"]): item for item in payload}


def build_articles_and_diff(
    article_limit: int,
    target_store_name: str,
) -> tuple[list[dict[str, object]], list[UploadDocument], dict[str, int], dict[str, object]]:
    previous_manifest = load_manifest()
    selection = fetch_articles(limit=article_limit)
    articles = selection.selected_articles
    next_manifest: list[dict[str, object]] = []
    upload_documents_list: list[UploadDocument] = []

    counts = {
        "total_scraped": len(articles),
        "added": 0,
        "updated": 0,
        "skipped": 0,
    }
    diagnostics = {
        "total_available": selection.total_available,
        "total_fetched": selection.total_fetched,
        "selected": len(articles),
        "priority_selected_count": selection.priority_selected_count,
        "excluded_dashboard_count": selection.excluded_dashboard_count,
        "article_limit": selection.article_limit,
        "first_10_selected_titles": [article.title for article in articles[:10]],
    }

    for article in articles:
        rendered = render_article_markdown(
            article_id=article.article_id,
            title=article.title,
            updated_at=article.updated_at,
            article_url=article.html_url,
            html_body=article.body,
        )
        destination = ARTICLES_DIR / f"{rendered.slug}.md"
        destination.write_text(rendered.content, encoding="utf-8")

        manifest_entry = {
            "article_id": article.article_id,
            "title": article.title,
            "slug": rendered.slug,
            "path": str(destination.relative_to(PROJECT_ROOT)),
            "sha256": rendered.sha256,
            "updated_at": article.updated_at,
            "article_url": article.html_url,
        }
        next_manifest.append(manifest_entry)

        previous = previous_manifest.get(article.article_id)
        if previous is None:
            counts["added"] += 1
            upload_documents_list.append(
                UploadDocument(
                    article_id=article.article_id,
                    title=article.title,
                    path=destination,
                    sha256=rendered.sha256,
                )
            )
            continue

        if previous.get("uploaded_store_name") != target_store_name:
            counts["added"] += 1
            upload_documents_list.append(
                UploadDocument(
                    article_id=article.article_id,
                    title=article.title,
                    path=destination,
                    sha256=rendered.sha256,
                )
            )
            continue

        if previous.get("sha256") != rendered.sha256:
            counts["updated"] += 1
            upload_documents_list.append(
                UploadDocument(
                    article_id=article.article_id,
                    title=article.title,
                    path=destination,
                    sha256=rendered.sha256,
                )
            )
            continue

        counts["skipped"] += 1

    return next_manifest, upload_documents_list, counts, diagnostics


def apply_upload_metadata(
    manifest_entries: list[dict[str, object]],
    uploaded_documents,
    store_name: str,
) -> list[dict[str, object]]:
    uploaded_by_article_id = {item.article_id: item for item in uploaded_documents}
    updated_manifest: list[dict[str, object]] = []

    for entry in manifest_entries:
        enriched = dict(entry)
        article_id = int(enriched["article_id"])
        uploaded = uploaded_by_article_id.get(article_id)
        if uploaded:
            enriched["uploaded_store_name"] = store_name
            enriched["uploaded_document_name"] = uploaded.document_name
            enriched["upload_operation_name"] = uploaded.operation_name
        updated_manifest.append(enriched)

    return updated_manifest


def main() -> None:
    load_dotenv()
    ensure_directories()
    article_limit = get_article_limit()
    client = build_client()
    store_name, _ = ensure_file_search_store(client)

    try:
        manifest_entries, changed_documents, counts, diagnostics = build_articles_and_diff(
            article_limit,
            store_name,
        )
    except RequestException as exc:
        print(f"Network/API error while fetching help center articles: {exc}")
        raise

    upload_result = upload_documents(
        changed_documents,
        client=client,
        store_name=store_name,
    )
    manifest_entries = apply_upload_metadata(
        manifest_entries,
        upload_result.uploaded_documents,
        upload_result.store_name,
    )
    write_json(MANIFEST_PATH, manifest_entries)

    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "total_scraped": counts["total_scraped"],
        "added": counts["added"],
        "updated": counts["updated"],
        "skipped": counts["skipped"],
        "uploaded": upload_result.uploaded_count,
        "store_name": upload_result.store_name,
        "selection": diagnostics,
    }
    write_json(LAST_RUN_PATH, summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


HELP_CENTER_API_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json"
DEFAULT_TIMEOUT_SECONDS = 30


@dataclass
class HelpCenterArticle:
    article_id: int
    title: str
    html_url: str
    body: str
    updated_at: str


def _request_page(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_articles(limit: int, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> list[HelpCenterArticle]:
    if limit <= 0:
        return []

    next_page: str | None = HELP_CENTER_API_URL
    collected: list[HelpCenterArticle] = []

    while next_page and len(collected) < limit:
        payload = _request_page(next_page, timeout=timeout)
        articles = payload.get("articles", [])

        for article in articles:
            body = (article.get("body") or "").strip()
            if not body:
                continue

            collected.append(
                HelpCenterArticle(
                    article_id=int(article["id"]),
                    title=(article.get("title") or "").strip(),
                    html_url=(article.get("html_url") or "").strip(),
                    body=body,
                    updated_at=(article.get("updated_at") or "").strip(),
                )
            )

            if len(collected) >= limit:
                break

        next_page = payload.get("next_page")

    return collected

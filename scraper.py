from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests


HELP_CENTER_API_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json"
DEFAULT_TIMEOUT_SECONDS = 30
CANONICAL_YOUTUBE_ARTICLE_ID = 360051014713
PLAYLIST_DEMO_ARTICLE_ID = 28295104605843
VIMEO_DEMO_ARTICLE_ID = 360016254994
SUPPORTED_FILES_ARTICLE_ID = 360016342373
DASHBOARD_TERMS = ("youtube dashboard", "dashboard", "analytics", "looker studio")


@dataclass
class HelpCenterArticle:
    article_id: int
    title: str
    html_url: str
    body: str
    updated_at: str


@dataclass
class ArticleSelectionResult:
    total_available: int
    total_fetched: int
    article_limit: int
    priority_selected_count: int
    excluded_dashboard_count: int
    selected_articles: list[HelpCenterArticle]


def _request_page(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _parse_updated_at(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized)


def _article_text(article: HelpCenterArticle) -> str:
    return f"{article.title} {article.html_url} {article.body}".lower()


def _is_dashboard_article(article: HelpCenterArticle) -> bool:
    text = _article_text(article)
    return any(term in text for term in DASHBOARD_TERMS)


def _matches_demo_article(article: HelpCenterArticle, article_id: int) -> bool:
    return article.article_id == article_id


def _priority_pinned_articles(articles: list[HelpCenterArticle]) -> list[HelpCenterArticle]:
    pinned_ids = [
        CANONICAL_YOUTUBE_ARTICLE_ID,
        PLAYLIST_DEMO_ARTICLE_ID,
        VIMEO_DEMO_ARTICLE_ID,
        SUPPORTED_FILES_ARTICLE_ID,
    ]
    by_id = {article.article_id: article for article in articles}
    pinned: list[HelpCenterArticle] = []
    for article_id in pinned_ids:
        article = by_id.get(article_id)
        if article:
            pinned.append(article)
    return pinned


def fetch_articles(limit: int, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> ArticleSelectionResult:
    if limit <= 0:
        return ArticleSelectionResult(
            total_available=0,
            total_fetched=0,
            article_limit=limit,
            priority_selected_count=0,
            excluded_dashboard_count=0,
            selected_articles=[],
        )

    next_page: str | None = HELP_CENTER_API_URL
    deduped_articles: dict[int, HelpCenterArticle] = {}
    total_available = 0

    while next_page:
        payload = _request_page(next_page, timeout=timeout)
        total_available = max(total_available, int(payload.get("count") or 0))
        articles = payload.get("articles", [])

        for article in articles:
            body = (article.get("body") or "").strip()
            if not body:
                continue

            article_id = int(article["id"])
            deduped_articles[article_id] = HelpCenterArticle(
                article_id=article_id,
                title=(article.get("title") or "").strip(),
                html_url=(article.get("html_url") or "").strip(),
                body=body,
                updated_at=(article.get("updated_at") or "").strip(),
            )

        next_page = payload.get("next_page")

    all_articles = list(deduped_articles.values())
    dashboard_articles = [article for article in all_articles if _is_dashboard_article(article)]
    non_dashboard_articles = [article for article in all_articles if not _is_dashboard_article(article)]
    source_articles = non_dashboard_articles if len(non_dashboard_articles) >= limit else all_articles
    excluded_dashboard_count = len(dashboard_articles) if source_articles is non_dashboard_articles else 0

    pinned_articles = _priority_pinned_articles(source_articles)
    selected_ids = {article.article_id for article in pinned_articles}
    remaining_slots = max(limit - len(pinned_articles), 0)
    recent_articles = sorted(
        (article for article in source_articles if article.article_id not in selected_ids),
        key=lambda article: (
            -_parse_updated_at(article.updated_at).timestamp(),
            article.title.lower(),
        ),
    )
    selected_articles = (pinned_articles + recent_articles[:remaining_slots])[:limit]

    return ArticleSelectionResult(
        total_available=total_available or len(all_articles),
        total_fetched=len(all_articles),
        article_limit=limit,
        priority_selected_count=len(pinned_articles),
        excluded_dashboard_count=excluded_dashboard_count,
        selected_articles=selected_articles,
    )

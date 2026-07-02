from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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


@dataclass
class ArticleSelectionResult:
    total_available: int
    total_fetched: int
    article_limit: int
    priority_selected_count: int
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


def _article_priority_score(article: HelpCenterArticle) -> int:
    title = article.title.lower()
    url = article.html_url.lower()
    body = article.body.lower()

    score = 0

    title_has_youtube = "youtube" in title
    title_has_video = "video" in title
    text_has_youtube = "youtube" in f"{title} {url} {body}"
    text_has_video = "video" in f"{title} {url} {body}"

    if text_has_youtube:
        score += 20
    if text_has_video:
        score += 16
    if title_has_youtube:
        score += 40
    if title_has_video:
        score += 35
    if title_has_youtube and title_has_video:
        score += 90
    if text_has_youtube and text_has_video:
        score += 30

    if "youtube app" in title:
        score += 50
    if "youtube video" in title:
        score += 60
    if "add youtube" in title or "youtube add" in title:
        score += 40

    add_terms = ("add ", "adding", "upload", "use ", "using", "play")
    if any(term in title for term in add_terms):
        score += 18
    if "app" in title:
        score += 20
    if "youtube" in url and "video" in url:
        score += 20
    if "youtube app" in body:
        score += 15
    if "youtube video" in body:
        score += 15

    for penalty_term in ("dashboard", "analytics", "looker studio"):
        if penalty_term in title:
            score -= 120
        elif penalty_term in url:
            score -= 60
        elif penalty_term in body:
            score -= 30

    return score


def fetch_articles(limit: int, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> ArticleSelectionResult:
    if limit <= 0:
        return ArticleSelectionResult(
            total_available=0,
            total_fetched=0,
            article_limit=limit,
            priority_selected_count=0,
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
    scored_articles = sorted(
        all_articles,
        key=lambda article: (
            -_article_priority_score(article),
            -_parse_updated_at(article.updated_at).timestamp(),
            article.title.lower(),
        ),
    )
    priority_articles = [article for article in scored_articles if _article_priority_score(article) > 0]
    selected_priority = priority_articles[:limit]

    selected_ids = {article.article_id for article in selected_priority}
    remaining_slots = max(limit - len(selected_priority), 0)
    recent_articles = sorted(
        (article for article in all_articles if article.article_id not in selected_ids),
        key=lambda article: (
            -_parse_updated_at(article.updated_at).timestamp(),
            article.title.lower(),
        ),
    )
    selected_articles = selected_priority + recent_articles[:remaining_slots]

    return ArticleSelectionResult(
        total_available=total_available or len(all_articles),
        total_fetched=len(all_articles),
        article_limit=limit,
        priority_selected_count=len(selected_priority),
        selected_articles=selected_articles,
    )

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup
from markdownify import markdownify as to_markdown
from slugify import slugify


REMOVE_SELECTORS = ("script", "style", "nav", "header", "footer", "form")
WHITESPACE_RE = re.compile(r"\n{3,}")
KEYWORD_SPLIT_RE = re.compile(r"[^a-z0-9]+")
STOP_WORDS = {"a", "an", "and", "for", "how", "in", "of", "on", "the", "to", "with"}


@dataclass
class RenderedMarkdownArticle:
    slug: str
    content: str
    sha256: str


def make_article_slug(title: str, article_id: int) -> str:
    candidate = slugify(title or "", lowercase=True)
    return candidate or str(article_id)


def strip_unwanted_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for selector in REMOVE_SELECTORS:
        for tag in soup.find_all(selector):
            tag.decompose()
    return str(soup)


def html_to_markdown(html: str) -> str:
    return to_markdown(
        html,
        heading_style="ATX",
        bullets="-",
        strip=REMOVE_SELECTORS,
    )


def normalize_markdown(markdown: str) -> str:
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    normalized = "\n".join(lines).strip()
    return WHITESPACE_RE.sub("\n\n", normalized)


def build_frontmatter(article_id: int, title: str, updated_at: str, article_url: str) -> str:
    escaped_title = title.replace('"', '\\"')
    return "\n".join(
        [
            "---",
            f"article_id: {article_id}",
            f'title: "{escaped_title}"',
            f'updated_at: "{updated_at}"',
            f'article_url: "{article_url}"',
            "---",
        ]
    )


def build_keywords(title: str) -> str:
    keywords: list[str] = []
    seen: set[str] = set()
    for token in KEYWORD_SPLIT_RE.split(title.lower()):
        keyword = token.strip()
        if len(keyword) < 3 or keyword in STOP_WORDS or keyword in seen:
            continue
        seen.add(keyword)
        keywords.append(keyword)
    return ", ".join(keywords)


def render_article_markdown(
    *,
    article_id: int,
    title: str,
    updated_at: str,
    article_url: str,
    html_body: str,
) -> RenderedMarkdownArticle:
    cleaned_html = strip_unwanted_html(html_body)
    body_markdown = normalize_markdown(html_to_markdown(cleaned_html))
    frontmatter = build_frontmatter(article_id, title, updated_at, article_url)
    keywords = build_keywords(title)

    metadata_lines = [
        f"# {title}",
        f"Article URL: {article_url}",
    ]
    if keywords:
        metadata_lines.append(f"Keywords: {keywords}")

    final_content = normalize_markdown(
        "\n\n".join(
            [
                frontmatter,
                "\n".join(metadata_lines),
                body_markdown,
            ]
        )
    )
    digest = hashlib.sha256(final_content.encode("utf-8")).hexdigest()

    return RenderedMarkdownArticle(
        slug=make_article_slug(title, article_id),
        content=final_content + "\n",
        sha256=digest,
    )

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup
from markdownify import markdownify as to_markdown
from slugify import slugify


REMOVE_SELECTORS = ("script", "style", "nav", "header", "footer", "form")
WHITESPACE_RE = re.compile(r"\n{3,}")


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

    final_content = normalize_markdown(
        "\n\n".join(
            [
                frontmatter,
                f"Article URL: {article_url}",
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

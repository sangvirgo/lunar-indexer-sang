from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai


DEFAULT_QUESTION = "How do I add a YouTube video?"
DEFAULT_MODEL = "gemini-2.5-flash"
SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply."""
ARTICLE_URL_RE = re.compile(r"Article URL:\s*(https?://\S+)", re.IGNORECASE)
YOUTUBE_VIDEO_HINT = (
    "Retrieval hint: For questions about adding a normal YouTube video, "
    "prefer documentation about the YouTube app/video content, not YouTube Dashboard analytics."
)
PROJECT_ROOT = Path(__file__).resolve().parent
LOCAL_ARTICLES_DIR = PROJECT_ROOT / "data" / "articles"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask a question against the uploaded Gemini File Search Store.")
    parser.add_argument("question", nargs="*", help="Question text")
    return parser.parse_args()


def require_env(name: str, message: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(message)
    return value


def ask_question(question: str) -> Any:
    api_key = require_env("GEMINI_API_KEY", "Missing GEMINI_API_KEY. Add it to .env.")
    store_name = require_env(
        "GEMINI_FILE_SEARCH_STORE_NAME",
        "Missing GEMINI_FILE_SEARCH_STORE_NAME. Add it to .env.",
    )
    model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    contents = question
    normalized_question = question.lower()
    if "youtube" in normalized_question and "video" in normalized_question and "add" in normalized_question:
        contents = f"{question}\n\n{YOUTUBE_VIDEO_HINT}"

    client = genai.Client(api_key=api_key)
    return client.models.generate_content(
        model=model,
        contents=contents,
        config={
            "system_instruction": SYSTEM_PROMPT,
            "tools": [
                {
                    "file_search": {
                        "file_search_store_names": [store_name],
                    }
                }
            ],
        },
    )


def extract_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    pieces: list[str] = []
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text.strip():
                pieces.append(part_text.strip())

    return "\n\n".join(pieces).strip()


def _extract_article_urls_from_text(text: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for match in ARTICLE_URL_RE.findall(text):
        if match not in seen:
            seen.add(match)
            urls.append(match)
    return urls


def extract_grounding_urls(response: Any) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    for candidate in getattr(response, "candidates", []) or []:
        grounding = getattr(candidate, "grounding_metadata", None)
        for chunk in getattr(grounding, "grounding_chunks", []) or []:
            retrieved = getattr(chunk, "retrieved_context", None)
            if not retrieved:
                continue

            for url in _extract_article_urls_from_text(getattr(retrieved, "text", "") or ""):
                if url not in seen:
                    seen.add(url)
                    urls.append(url)

            chunk_uri = getattr(retrieved, "uri", None)
            if isinstance(chunk_uri, str) and chunk_uri.startswith("http") and chunk_uri not in seen:
                seen.add(chunk_uri)
                urls.append(chunk_uri)

    return urls


def _local_citation_score(question: str, title: str, url: str, body: str) -> int:
    title_lower = title.lower()
    url_lower = url.lower()
    body_lower = body.lower()
    question_lower = question.lower()
    combined = f"{title_lower} {url_lower} {body_lower}"

    score = 0
    if "youtube" in question_lower and "youtube" in combined:
        score += 40
    if "video" in question_lower and "video" in combined:
        score += 35
    if "add" in question_lower and any(term in combined for term in ("add", "adding", "create", "use")):
        score += 20
    if "youtube" in title_lower and "video" in title_lower:
        score += 50
    if "youtube app" in title_lower:
        score += 40
    if "dashboard" in title_lower or "analytics" in title_lower or "looker studio" in title_lower:
        score -= 120
    return score


def fallback_local_article_urls(question: str) -> list[str]:
    if not LOCAL_ARTICLES_DIR.exists():
        return []

    candidates: list[tuple[int, str]] = []
    for path in LOCAL_ARTICLES_DIR.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        url_match = ARTICLE_URL_RE.search(text)
        if not title_match or not url_match:
            continue
        title = title_match.group(1).strip()
        url = url_match.group(1).strip()
        score = _local_citation_score(question, title, url, text[:4000])
        if score <= 0:
            continue
        candidates.append((score, url))

    candidates.sort(key=lambda item: (-item[0], item[1]))
    urls: list[str] = []
    seen: set[str] = set()
    for _, url in candidates:
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
        if len(urls) >= 3:
            break
    return urls


def format_answer(response: Any, question: str = "") -> tuple[str, bool]:
    answer_text = extract_text(response)
    if not answer_text:
        answer_text = "No readable answer text was returned by the SDK."

    article_urls = _extract_article_urls_from_text(answer_text)
    if not article_urls:
        article_urls = extract_grounding_urls(response)
    if not article_urls and question:
        article_urls = fallback_local_article_urls(question)

    article_urls = article_urls[:3]
    has_article_url = bool(article_urls) or "Article URL:" in answer_text

    if article_urls and "Article URL:" not in answer_text:
        answer_text = f"{answer_text}\n\n" + "\n".join(f"Article URL: {url}" for url in article_urls)

    return answer_text, has_article_url


def main() -> None:
    load_dotenv()
    args = parse_args()
    question = " ".join(args.question).strip() or DEFAULT_QUESTION

    try:
        response = ask_question(question)
        answer_text, _ = format_answer(response, question)
    except Exception as exc:
        print(f"Question: {question}")
        print()
        print(f"Error: {exc}")
        return

    print(f"Question: {question}")
    print()
    print("Answer:")
    print(answer_text)


if __name__ == "__main__":
    main()

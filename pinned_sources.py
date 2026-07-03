from __future__ import annotations

import re
from pathlib import Path


PINNED_SOURCES = [
    {
        "key": "youtube_video",
        "article_id": 360051014713,
        "title": "How to use YouTube with OptiSigns",
        "url": "https://support.optisigns.com/hc/en-us/articles/360051014713-How-to-use-YouTube-with-OptiSigns",
        "slug": "how-to-use-youtube-with-optisigns.md",
        "question_patterns": (
            "how do i add a youtube video",
            "add youtube video",
        ),
        "negative_terms": ("dashboard", "analytics", "looker studio"),
    },
    {
        "key": "add_screen",
        "article_id": 360016374813,
        "title": "Set up & add a screen",
        "url": "https://support.optisigns.com/hc/en-us/articles/360016374813-Set-up-add-a-screen",
        "slug": "set-up-add-a-screen.md",
        "question_patterns": (
            "how do i add a screen",
            "add screen",
            "pair screen",
        ),
        "negative_terms": (),
    },
    {
        "key": "vimeo_video",
        "article_id": 360016254994,
        "title": "How to add & use Vimeo video with OptiSigns",
        "url": "https://support.optisigns.com/hc/en-us/articles/360016254994-How-to-add-use-Vimeo-video-with-OptiSigns",
        "slug": "how-to-add-use-vimeo-video-with-optisigns.md",
        "question_patterns": (
            "how do i add a vimeo video",
            "add vimeo video",
        ),
        "negative_terms": (),
    },
    {
        "key": "supported_file_types",
        "article_id": 360016342373,
        "title": "What types of files are supported?",
        "url": "https://support.optisigns.com/hc/en-us/articles/360016342373-What-types-of-files-are-supported",
        "slug": "what-types-of-files-are-supported.md",
        "question_patterns": (
            "what file types are supported",
            "supported file types",
            "supported media formats",
        ),
        "negative_terms": (),
    },
]


def normalize_question_text(question: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", question.lower()).strip()


def find_pinned_source_for_question(question: str) -> dict | None:
    normalized = normalize_question_text(question)
    if not normalized:
        return None

    for source in PINNED_SOURCES:
        for pattern in source["question_patterns"]:
            if pattern in normalized:
                return dict(source)
    return None


def load_pinned_markdown(question: str, data_dir: Path = Path("data/articles")) -> dict | None:
    source = find_pinned_source_for_question(question)
    if not source:
        return None

    path = data_dir / source["slug"]
    payload = dict(source)
    payload["path"] = str(path)
    payload["status"] = "missing"
    payload["markdown"] = ""

    if path.exists():
        payload["status"] = "present"
        payload["markdown"] = path.read_text(encoding="utf-8")

    return payload

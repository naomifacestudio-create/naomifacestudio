"""Izvlačenje običnog teksta iz sadržaja za SEO fallback i čitljivost."""

from __future__ import annotations

import re

from page.plaintext import extract_page_plaintext

_WHITESPACE_RE = re.compile(r"\s+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+")


def normalize_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.strip())


def split_sentences(text: str) -> list[str]:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return []
    parts = _SENTENCE_SPLIT_RE.split(cleaned)
    return [part.strip() for part in parts if part.strip()]


def get_content_plain_text(page_object, *, visible_only=True, max_length=600) -> str:
    """Kombinuje uvod/excerpt i page JSON sadržaj za SEO i čitljivost."""
    _ = visible_only
    parts: list[str] = []

    excerpt = getattr(page_object, "excerpt", "") or ""
    if excerpt and excerpt.strip():
        parts.append(excerpt.strip())

    should_render_page = getattr(page_object, "should_render_page", None)
    if callable(should_render_page) and should_render_page():
        body_page = getattr(page_object, "body_page", None) or {}
        page_text = extract_page_plaintext(body_page)
        if page_text:
            parts.append(page_text)
    else:
        body_plaintext = getattr(page_object, "body_plaintext", "") or ""
        if body_plaintext and body_plaintext.strip():
            parts.append(body_plaintext.strip())

    combined = normalize_whitespace(" ".join(parts))
    return combined[:max_length]

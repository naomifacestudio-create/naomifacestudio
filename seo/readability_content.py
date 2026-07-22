"""Strukturirani sadržaj za analizu čitljivosti."""

from __future__ import annotations

from dataclasses import dataclass, field

from page.constants import BlockType as PageBlockType
from seo.content_text import get_content_plain_text, normalize_whitespace, split_sentences


@dataclass(frozen=True)
class HeadingEntry:
    level: str
    text: str


@dataclass(frozen=True)
class ReadabilityContentInput:
    content: str = ""
    sentences: list[str] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)
    headings: list[HeadingEntry] = field(default_factory=list)
    word_count: int = 0


def _split_paragraphs(text: str) -> list[str]:
    if not text:
        return []

    parts = re_split_paragraphs(text)
    return [normalize_whitespace(part) for part in parts if normalize_whitespace(part)]


def re_split_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    chunks = normalized.split("\n\n")
    if len(chunks) <= 1 and "\n" in normalized:
        chunks = normalized.split("\n")
    return chunks


def extract_readability_content(page_object, *, visible_only=False) -> ReadabilityContentInput:
    should_render_page = getattr(page_object, "should_render_page", None)
    if callable(should_render_page) and should_render_page():
        paragraphs: list[str] = []
        headings: list[HeadingEntry] = []

        excerpt = getattr(page_object, "excerpt", "") if page_object else ""
        if excerpt and excerpt.strip():
            paragraphs.extend(_split_paragraphs(excerpt.strip()))

        title = normalize_whitespace(getattr(page_object, "title", "") or "")
        if title:
            headings.append(HeadingEntry(level="h1", text=title))

        body_page = getattr(page_object, "body_page", None) or {}
        for section in body_page.get("sections") or []:
            for row in section.get("rows") or []:
                for column in row.get("columns") or []:
                    for block in column.get("blocks") or []:
                        if not isinstance(block, dict):
                            continue
                        block_type = block.get("type")
                        attrs = block.get("attrs") or {}
                        if block_type == PageBlockType.HEADING:
                            heading_text = normalize_whitespace(str(attrs.get("text", "")))
                            level = str(attrs.get("level", 2))
                            if heading_text:
                                headings.append(HeadingEntry(level=f"h{level}", text=heading_text))
                        if block_type == PageBlockType.TEXT:
                            paragraph_text = normalize_whitespace(str(attrs.get("text", "")))
                            if paragraph_text:
                                paragraphs.extend(_split_paragraphs(paragraph_text) or [paragraph_text])

        full_text = get_content_plain_text(page_object, visible_only=visible_only, max_length=20000)
        if not paragraphs and full_text:
            paragraphs = split_sentences(full_text) or [full_text]
        sentences = split_sentences(full_text)
        word_count = len(full_text.split()) if full_text else 0
        return ReadabilityContentInput(
            content=full_text.strip(),
            sentences=sentences,
            paragraphs=paragraphs,
            headings=headings,
            word_count=word_count,
        )

    full_text = get_content_plain_text(page_object, visible_only=visible_only, max_length=20000)
    paragraphs = _split_paragraphs(full_text) if full_text else []
    sentences = split_sentences(full_text)
    return ReadabilityContentInput(
        content=full_text.strip(),
        sentences=sentences,
        paragraphs=paragraphs,
        headings=[],
        word_count=len(full_text.split()) if full_text else 0,
    )


def build_readability_content_input(
    content_object,
    *,
    overrides: dict | None = None,
    visible_only: bool = False,
) -> ReadabilityContentInput:
    overrides = overrides or {}
    base = extract_readability_content(content_object, visible_only=visible_only)

    excerpt = overrides.get("excerpt", "").strip()
    if excerpt:
        paragraphs = _split_paragraphs(excerpt)
        if paragraphs:
            content = normalize_whitespace(excerpt)
            if base.content and excerpt not in base.content:
                content = normalize_whitespace(f"{excerpt} {base.content}")
            return ReadabilityContentInput(
                content=content,
                sentences=split_sentences(content),
                paragraphs=paragraphs + base.paragraphs,
                headings=base.headings,
                word_count=len(content.split()),
            )

    return base

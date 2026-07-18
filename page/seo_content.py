"""SEO helperi za iv_page_v1 sadržaj."""

from __future__ import annotations

from typing import Any

from page.constants import BlockType
from page.plaintext import extract_page_plaintext
import re


def normalize_whitespace(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _iter_page_blocks(page: dict[str, Any]):
    for section in page.get("sections") or []:
        if not isinstance(section, dict):
            continue
        for row in section.get("rows") or []:
            if not isinstance(row, dict):
                continue
            for column in row.get("columns") or []:
                if not isinstance(column, dict):
                    continue
                for block in column.get("blocks") or []:
                    if isinstance(block, dict):
                        yield block


def extract_page_analysis_parts(content_object, *, visible_only=True) -> dict:
    _ = visible_only
    page = getattr(content_object, "body_page", None) or {}
    if not isinstance(page, dict) or not page.get("sections"):
        return {
            "h1": "",
            "first_paragraph": "",
            "content": "",
            "image_alt_texts": [],
            "image_count": 0,
            "images_with_alt": 0,
        }

    h1 = normalize_whitespace(getattr(content_object, "title", "") or "")
    first_heading = ""
    first_paragraph = ""
    content_chunks: list[str] = []
    image_alt_texts: list[str] = []
    image_count = 0
    images_with_alt = 0

    for block in _iter_page_blocks(page):
        block_type = block.get("type")
        attrs = block.get("attrs") or {}
        if not isinstance(attrs, dict):
            attrs = {}

        if block_type in {BlockType.HEADING, BlockType.TEXT}:
            from page.rich_text import inline_html_to_plaintext

            plain = normalize_whitespace(inline_html_to_plaintext(str(attrs.get("text", ""))))
            if plain:
                content_chunks.append(plain)
                if block_type == BlockType.HEADING and not first_heading:
                    first_heading = plain
                if block_type == BlockType.TEXT and not first_paragraph:
                    first_paragraph = plain

        if block_type == BlockType.IMAGE:
            src = str(attrs.get("src") or attrs.get("path") or "").strip()
            alt = str(attrs.get("alt") or "").strip()
            if src:
                image_count += 1
                if alt:
                    images_with_alt += 1
                    image_alt_texts.append(alt)

        if block_type == BlockType.BUTTON:
            label = normalize_whitespace(str(attrs.get("label", "")))
            if label:
                content_chunks.append(label)

    if not h1 and first_heading:
        h1 = first_heading

    return {
        "h1": h1,
        "first_paragraph": first_paragraph,
        "content": normalize_whitespace(extract_page_plaintext(page)),
        "image_alt_texts": image_alt_texts,
        "image_count": image_count,
        "images_with_alt": images_with_alt,
    }

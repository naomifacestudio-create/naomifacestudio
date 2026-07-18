"""Izvlačenje običnog teksta iz iv_page_v1 za pretragu i SEO."""

from __future__ import annotations

from typing import Any

from page.constants import BlockType
from page.normalize import normalize_page
from page.rich_text import inline_html_to_plaintext
from page.schema import is_supported_page


def extract_page_plaintext(page: Any) -> str:
    if not is_supported_page(page):
        return ""

    normalized = normalize_page(page)
    parts: list[str] = []
    for section in normalized.get("sections") or []:
        for row in section.get("rows") or []:
            for column in row.get("columns") or []:
                for block in column.get("blocks") or []:
                    text = _block_plaintext(block)
                    if text:
                        parts.append(text)

    return "\n\n".join(parts).strip()


def _block_plaintext(block: Any) -> str:
    if not isinstance(block, dict):
        return ""

    block_type = block.get("type")
    attrs = block.get("attrs") or {}
    if not isinstance(attrs, dict):
        attrs = {}

    if block_type in {BlockType.HEADING, BlockType.TEXT}:
        return inline_html_to_plaintext(str(attrs.get("text", "")))

    if block_type == BlockType.BUTTON:
        return str(attrs.get("label", "")).strip()

    if block_type == BlockType.IMAGE:
        alt = str(attrs.get("alt", "")).strip()
        caption = str(attrs.get("caption", "")).strip()
        return " ".join(part for part in (alt, caption) if part)

    if block_type == BlockType.VIDEO:
        url = str(attrs.get("url", "")).strip()
        caption = str(attrs.get("caption", "")).strip()
        return " ".join(part for part in (url, caption) if part)

    if block_type == BlockType.FAQ:
        parts = []
        for item in attrs.get("items") or []:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question", "")).strip()
            answer = str(item.get("answer", "")).strip()
            if question:
                parts.append(question)
            if answer:
                parts.append(answer)
        return "\n".join(parts)

    return ""

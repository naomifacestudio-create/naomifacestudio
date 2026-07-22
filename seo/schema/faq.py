"""Izvlačenje FAQ parova iz iv_page_v1 za FAQPage šemu."""

from __future__ import annotations

from dataclasses import dataclass

from page.constants import BlockType


@dataclass(frozen=True)
class FaqItem:
    question: str
    answer: str


def extract_faq_items(page_object, *, visible_only: bool = True) -> list[FaqItem]:
    _ = visible_only
    if page_object is None or not getattr(page_object, "pk", None):
        return []

    should_render_page = getattr(page_object, "should_render_page", None)
    if not callable(should_render_page) or not should_render_page():
        return []

    body_page = getattr(page_object, "body_page", None) or {}
    items: list[FaqItem] = []

    for section in body_page.get("sections") or []:
        for row in section.get("rows") or []:
            for column in row.get("columns") or []:
                for block in column.get("blocks") or []:
                    if not isinstance(block, dict) or block.get("type") != BlockType.FAQ:
                        continue
                    attrs = block.get("attrs") or {}
                    for raw in attrs.get("items") or []:
                        if not isinstance(raw, dict):
                            continue
                        question = str(raw.get("question", "")).strip()
                        answer = str(raw.get("answer", "")).strip()
                        if question and answer:
                            items.append(FaqItem(question=question, answer=answer))

    return _dedupe_faq_items(items)


def _dedupe_faq_items(items: list[FaqItem]) -> list[FaqItem]:
    seen: set[tuple[str, str]] = set()
    unique: list[FaqItem] = []
    for item in items:
        key = (item.question.lower(), item.answer.lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique

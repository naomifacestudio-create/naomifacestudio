"""Pomoćne funkcije za interni page JSON."""

from __future__ import annotations

from typing import Any

from page.constants import PAGE_FORMAT_V1, SUPPORTED_PAGE_FORMATS, RootType


def empty_page() -> dict[str, Any]:
    return {
        "format": PAGE_FORMAT_V1,
        "type": RootType.PAGE,
        "sections": [],
    }


def is_supported_page(page: Any) -> bool:
    if not isinstance(page, dict):
        return False

    page_format = page.get("format")
    if page_format not in SUPPORTED_PAGE_FORMATS:
        return False

    if page.get("type") != RootType.PAGE:
        return False

    sections = page.get("sections")
    if not isinstance(sections, list):
        return False

    return True


def page_has_content(page: Any) -> bool:
    if not is_supported_page(page):
        return False
    return len(page["sections"]) > 0

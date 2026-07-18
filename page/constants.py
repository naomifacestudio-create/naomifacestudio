"""Zaključana specifikacija internog page formata (iv_page_v1)."""

from __future__ import annotations

from enum import StrEnum


PAGE_FORMAT_V1 = "iv_page_v1"

SUPPORTED_PAGE_FORMATS = frozenset({PAGE_FORMAT_V1})


class RootType(StrEnum):
    PAGE = "page"


class BlockType(StrEnum):
    HEADING = "heading"
    TEXT = "text"
    BUTTON = "button"
    IMAGE = "image"
    VIDEO = "video"
    FAQ = "faq"
    DIVIDER = "divider"


SECTION_BLOCK_TYPES = frozenset({member.value for member in BlockType})

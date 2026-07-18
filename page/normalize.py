"""Normalizacija page JSON-a u structure-first oblik (section → rows → columns)."""

from __future__ import annotations

import copy
from typing import Any

from page.constants import BlockType
from page.ids import new_row_id
from page.rich_text import sanitize_inline_html
from page.schema import is_supported_page
from page.structure import DEFAULT_ROW_SETTINGS, DEFAULT_SECTION_SETTINGS

_SECTION_SPACING_KEYS = frozenset(
    {"padding_top", "padding_bottom", "margin_top", "margin_bottom", "row_gap"}
)
_ROW_SPACING_KEYS = frozenset({"column_gap"})
_COLUMN_SPACING_KEYS = frozenset({"padding"})


def _without_keys(settings: dict[str, Any], keys: frozenset[str]) -> dict[str, Any]:
    return {key: value for key, value in settings.items() if key not in keys}


def normalize_page(page: Any) -> dict[str, Any]:
    if not is_supported_page(page):
        return page

    normalized = copy.deepcopy(page)
    sections = []
    for section in normalized.get("sections") or []:
        if isinstance(section, dict):
            sections.append(_normalize_section(section))
    normalized["sections"] = sections
    return _sanitize_text_blocks(normalized)


def _sanitize_text_blocks(page: dict[str, Any]) -> dict[str, Any]:
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
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") not in {BlockType.TEXT, BlockType.HEADING}:
                        continue
                    attrs = block.setdefault("attrs", {})
                    if isinstance(attrs, dict) and isinstance(attrs.get("text"), str):
                        attrs["text"] = sanitize_inline_html(attrs["text"])
    return page


def _normalize_section(section: dict[str, Any]) -> dict[str, Any]:
    from page.rich_text import normalize_hex_color

    result = dict(section)
    settings = result.get("settings")
    if not isinstance(settings, dict):
        result["settings"] = dict(DEFAULT_SECTION_SETTINGS)
    else:
        merged = dict(DEFAULT_SECTION_SETTINGS)
        merged.update(_without_keys(settings, _SECTION_SPACING_KEYS))
        raw_color = merged.get("background_color", "")
        merged["background_color"] = normalize_hex_color(raw_color) if raw_color else ""
        result["settings"] = merged

    rows = result.get("rows")
    if isinstance(rows, list) and rows:
        result["rows"] = [_normalize_row(row) for row in rows if isinstance(row, dict)]
        return result

    columns = result.get("columns")
    if isinstance(columns, list) and columns:
        result["rows"] = [
            {
                "id": new_row_id(),
                "settings": dict(DEFAULT_ROW_SETTINGS),
                "columns": [_normalize_column(column, index) for index, column in enumerate(columns)],
            }
        ]
        result.pop("columns", None)
        result.pop("layout_id", None)
        result.pop("template_id", None)
        result.pop("variant_id", None)
        result.pop("template_version", None)
        return result

    result["rows"] = []
    return result


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    settings = result.get("settings")
    if not isinstance(settings, dict):
        result["settings"] = dict(DEFAULT_ROW_SETTINGS)
    else:
        merged = dict(DEFAULT_ROW_SETTINGS)
        merged.update(_without_keys(settings, _ROW_SPACING_KEYS))
        result["settings"] = merged
    columns = result.get("columns")
    if not isinstance(columns, list):
        result["columns"] = []
    else:
        result["columns"] = [
            _normalize_column(column, index) for index, column in enumerate(columns) if isinstance(column, dict)
        ]
    return result


def _normalize_column(column: dict[str, Any], index: int) -> dict[str, Any]:
    from page.structure import DEFAULT_COLUMN_SETTINGS

    result = dict(column)
    settings = result.get("settings")
    if not isinstance(settings, dict):
        legacy_index = result.pop("index", index)
        width = 12
        if isinstance(legacy_index, int) and legacy_index >= 0:
            width = 12
        merged = dict(DEFAULT_COLUMN_SETTINGS)
        merged["width_desktop"] = width
        merged["width_tablet"] = width
        result["settings"] = merged
    else:
        merged = dict(DEFAULT_COLUMN_SETTINGS)
        merged.update(_without_keys(settings, _COLUMN_SPACING_KEYS))
        result["settings"] = merged
    blocks = result.get("blocks")
    if not isinstance(blocks, list):
        result["blocks"] = []
    return result

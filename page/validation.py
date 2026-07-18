"""Validacija iv_page_v1 strukture (structure-first)."""

from __future__ import annotations

from typing import Any

from page.constants import SECTION_BLOCK_TYPES, BlockType
from page.normalize import normalize_page
from page.schema import is_supported_page
from page.structure import ROW_PRESETS, MEDIA_WIDTH_PERCENT_MAX, MEDIA_WIDTH_PERCENT_MIN
from page.rich_text import is_safe_href, normalize_hex_color

_ALLOWED_ALIGN = frozenset({"left", "center", "right"})
_ALLOWED_VERTICAL_ALIGN = frozenset({"top", "center", "bottom"})
_ALLOWED_BACKGROUND = frozenset({"default", "light", "dark", "accent"})
_ALLOWED_CONTAINER = frozenset({"contained", "full"})


class PageValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_page(page: Any) -> list[str]:
    if not is_supported_page(page):
        return ["Stranica mora biti iv_page_v1 sa listom sections."]

    normalized = normalize_page(page)
    errors: list[str] = []
    sections = normalized.get("sections") or []
    for index, section in enumerate(sections):
        _validate_section(section, errors, path=f"sections[{index}]")
    return errors


def validate_page_or_raise(page: Any) -> None:
    errors = validate_page(page)
    if errors:
        raise PageValidationError(errors)


def _validate_section(section: Any, errors: list[str], *, path: str) -> None:
    if not isinstance(section, dict):
        errors.append(f"{path}: sekcija mora biti objekat.")
        return

    section_id = section.get("id")
    if not isinstance(section_id, str) or not section_id.strip():
        errors.append(f"{path}: nedostaje id.")

    settings = section.get("settings")
    if settings is not None and not isinstance(settings, dict):
        errors.append(f"{path}: settings mora biti objekat.")
    elif isinstance(settings, dict):
        _validate_section_settings(settings, errors, path=f"{path}.settings")

    rows = section.get("rows")
    if not isinstance(rows, list):
        errors.append(f"{path}: rows mora biti lista.")
        return

    for row_index, row in enumerate(rows):
        _validate_row(row, errors, path=f"{path}.rows[{row_index}]")


def _validate_section_settings(settings: dict[str, Any], errors: list[str], *, path: str) -> None:
    for key, allowed in (
        ("background", _ALLOWED_BACKGROUND),
        ("container_width", _ALLOWED_CONTAINER),
    ):
        value = settings.get(key)
        if value is not None and value not in allowed:
            errors.append(f"{path}.{key}: nevažeća vrednost '{value}'.")

    background_color = settings.get("background_color")
    if background_color is not None and not isinstance(background_color, str):
        errors.append(f"{path}.background_color: mora biti string.")
    elif isinstance(background_color, str) and background_color.strip():
        if not normalize_hex_color(background_color):
            errors.append(f"{path}.background_color: unesite validan hex (#RGB ili #RRGGBB).")


def _validate_row(row: Any, errors: list[str], *, path: str) -> None:
    if not isinstance(row, dict):
        errors.append(f"{path}: red mora biti objekat.")
        return

    row_id = row.get("id")
    if not isinstance(row_id, str) or not row_id.strip():
        errors.append(f"{path}: nedostaje id.")

    settings = row.get("settings")
    if settings is not None and not isinstance(settings, dict):
        errors.append(f"{path}: settings mora biti objekat.")
    elif isinstance(settings, dict):
        valign = settings.get("vertical_align")
        if valign is not None and valign not in _ALLOWED_VERTICAL_ALIGN:
            errors.append(f"{path}.settings.vertical_align: nevažeća vrednost.")

    columns = row.get("columns")
    if not isinstance(columns, list) or not columns:
        errors.append(f"{path}: red mora imati bar jednu kolonu.")
        return

    total_desktop = 0
    for col_index, column in enumerate(columns):
        _validate_column(column, errors, path=f"{path}.columns[{col_index}]")
        col_settings = column.get("settings") or {}
        width = col_settings.get("width_desktop", 12)
        if isinstance(width, int):
            total_desktop += width

    if total_desktop > 12:
        errors.append(f"{path}: zbir širina kolona na desktopu ne sme biti veći od 12.")


def _validate_column(column: Any, errors: list[str], *, path: str) -> None:
    if not isinstance(column, dict):
        errors.append(f"{path}: kolona mora biti objekat.")
        return

    column_id = column.get("id")
    if not isinstance(column_id, str) or not column_id.strip():
        errors.append(f"{path}: nedostaje id.")

    settings = column.get("settings")
    if settings is not None and not isinstance(settings, dict):
        errors.append(f"{path}: settings mora biti objekat.")
    elif isinstance(settings, dict):
        for width_key in ("width_mobile", "width_tablet", "width_desktop"):
            width = settings.get(width_key)
            if width is not None and (not isinstance(width, int) or width < 1 or width > 12):
                errors.append(f"{path}.settings.{width_key}: mora biti 1–12.")
        align = settings.get("horizontal_align")
        if align is not None and align not in _ALLOWED_ALIGN:
            errors.append(f"{path}.settings.horizontal_align: nevažeća vrednost.")

    blocks = column.get("blocks")
    if not isinstance(blocks, list):
        errors.append(f"{path}: blocks mora biti lista.")
        return

    for block_index, block in enumerate(blocks):
        _validate_block(block, errors, path=f"{path}.blocks[{block_index}]")


def _validate_block(block: Any, errors: list[str], *, path: str) -> None:
    if not isinstance(block, dict):
        errors.append(f"{path}: element mora biti objekat.")
        return

    block_id = block.get("id")
    if not isinstance(block_id, str) or not block_id.strip():
        errors.append(f"{path}: nedostaje id.")

    block_type = block.get("type")
    if not isinstance(block_type, str) or block_type not in SECTION_BLOCK_TYPES:
        errors.append(f"{path}: nepoznat ili nedostajući type.")
        return

    settings = block.get("settings")
    if settings is not None and not isinstance(settings, dict):
        errors.append(f"{path}: settings mora biti objekat.")
    elif isinstance(settings, dict):
        align = settings.get("align")
        if align is not None and align not in _ALLOWED_ALIGN:
            errors.append(f"{path}.settings.align: nevažeća vrednost.")
        width_percent = settings.get("width_percent")
        if width_percent is not None:
            try:
                width_value = int(str(width_percent).strip())
            except (TypeError, ValueError):
                errors.append(f"{path}.settings.width_percent: mora biti ceo broj.")
            else:
                if not MEDIA_WIDTH_PERCENT_MIN <= width_value <= MEDIA_WIDTH_PERCENT_MAX:
                    errors.append(
                        f"{path}.settings.width_percent: mora biti između "
                        f"{MEDIA_WIDTH_PERCENT_MIN} i {MEDIA_WIDTH_PERCENT_MAX}."
                    )

    attrs = block.get("attrs")
    if attrs is not None and not isinstance(attrs, dict):
        errors.append(f"{path}: attrs mora biti objekat.")
        return

    attrs = attrs or {}

    if block_type == BlockType.HEADING:
        level = attrs.get("level")
        if level not in {1, 2, 3, 4}:
            errors.append(f"{path}: heading level mora biti 1–4.")
        if not isinstance(attrs.get("text"), str):
            errors.append(f"{path}: heading text mora biti string.")

    elif block_type == BlockType.TEXT:
        if not isinstance(attrs.get("text"), str):
            errors.append(f"{path}: text mora biti string.")

    elif block_type == BlockType.BUTTON:
        if not isinstance(attrs.get("label"), str):
            errors.append(f"{path}: button label mora biti string.")
        href = attrs.get("href")
        if not isinstance(href, str):
            errors.append(f"{path}: button href mora biti string.")
        elif href.strip() and not _is_safe_href(href):
            errors.append(f"{path}: button href nije dozvoljen.")

    elif block_type == BlockType.IMAGE:
        src = attrs.get("src") or attrs.get("path") or ""
        if src and not isinstance(src, str):
            errors.append(f"{path}: image src mora biti string.")
        alt = attrs.get("alt")
        if alt is not None and not isinstance(alt, str):
            errors.append(f"{path}: image alt mora biti string.")
        if isinstance(src, str) and src.strip() and not str(alt or "").strip():
            errors.append(f"{path}: slika mora imati alt tekst.")
        media_asset_id = attrs.get("media_asset_id")
        if media_asset_id is not None and not isinstance(media_asset_id, str):
            errors.append(f"{path}: media_asset_id mora biti string.")

    elif block_type == BlockType.VIDEO:
        url = str(attrs.get("url") or "").strip()
        path = str(attrs.get("path") or attrs.get("src") or "").strip()
        if url and not isinstance(attrs.get("url"), str):
            errors.append(f"{path}: video url mora biti string.")
        elif url:
            from page.blocks.youtube import is_youtube_url

            if not is_youtube_url(url):
                errors.append(f"{path}: video url mora biti validan YouTube link.")
        elif not path:
            pass
        elif not isinstance(path, str):
            errors.append(f"{path}: video path mora biti string.")
        aspect = (block.get("settings") or {}).get("aspect")
        if aspect is not None and aspect not in {"16:9", "4:3"}:
            errors.append(f"{path}: video aspect mora biti 16:9 ili 4:3.")

    elif block_type == BlockType.FAQ:
        style = attrs.get("style")
        if style not in {"accordion", "list"}:
            errors.append(f"{path}: faq style mora biti accordion ili list.")
        items = attrs.get("items")
        if not isinstance(items, list) or not items:
            errors.append(f"{path}: faq mora imati bar jedno pitanje.")
        else:
            for item_index, item in enumerate(items):
                if not isinstance(item, dict):
                    errors.append(f"{path}.items[{item_index}]: stavka mora biti objekat.")
                    continue
                if not isinstance(item.get("question"), str):
                    errors.append(f"{path}.items[{item_index}]: question mora biti string.")
                if not isinstance(item.get("answer"), str):
                    errors.append(f"{path}.items[{item_index}]: answer mora biti string.")

    elif block_type == BlockType.DIVIDER:
        return


def is_valid_row_preset(preset: str) -> bool:
    return preset in ROW_PRESETS


def _is_safe_href(href: str) -> bool:
    return is_safe_href(href)

"""Validacija iv_page_v1 strukture (structure-first)."""

from __future__ import annotations

from typing import Any

from page.constants import SECTION_BLOCK_TYPES, BlockType
from page.normalize import normalize_page
from page.rich_text import is_safe_href, normalize_hex_color
from page.schema import is_supported_page
from page.structure import ROW_PRESETS, MEDIA_WIDTH_PERCENT_MAX, MEDIA_WIDTH_PERCENT_MIN

_ALLOWED_ALIGN = frozenset({"left", "center", "right"})
_ALLOWED_VERTICAL_ALIGN = frozenset({"top", "center", "bottom"})
_ALLOWED_BACKGROUND = frozenset({"default", "light", "dark", "accent"})
_ALLOWED_CONTAINER = frozenset({"contained", "full"})

_BLOCK_LABELS = {
    BlockType.HEADING: "Naslov",
    BlockType.TEXT: "Tekst",
    BlockType.BUTTON: "Dugme",
    BlockType.IMAGE: "Slika",
    BlockType.VIDEO: "Video",
    BlockType.FAQ: "FAQ",
    BlockType.DIVIDER: "Linija",
}


class PageValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_page(page: Any) -> list[str]:
    if not is_supported_page(page):
        return ["Sadržaj stranice nije u ispravnom formatu."]

    normalized = normalize_page(page)
    errors: list[str] = []
    sections = normalized.get("sections") or []
    for index, section in enumerate(sections):
        _validate_section(section, errors, section_index=index)
    return errors


def validate_page_or_raise(page: Any) -> None:
    errors = validate_page(page)
    if errors:
        raise PageValidationError(errors)


def _where(*, section: int, row: int | None = None, column: int | None = None) -> str:
    parts = [f"sekciji {section + 1}"]
    if row is not None:
        parts.append(f"redu {row + 1}")
    if column is not None:
        parts.append(f"koloni {column + 1}")
    return ", ".join(parts)


def _error(errors: list[str], where: str, message: str) -> None:
    errors.append(f"U {where}: {message}")


def _validate_section(section: Any, errors: list[str], *, section_index: int) -> None:
    where = _where(section=section_index)
    if not isinstance(section, dict):
        _error(errors, where, "sekcija nije ispravna.")
        return

    section_id = section.get("id")
    if not isinstance(section_id, str) or not section_id.strip():
        _error(errors, where, "sekciji nedostaje identifikator.")

    settings = section.get("settings")
    if settings is not None and not isinstance(settings, dict):
        _error(errors, where, "podešavanja sekcije nisu ispravna.")
    elif isinstance(settings, dict):
        _validate_section_settings(settings, errors, where=where)

    rows = section.get("rows")
    if not isinstance(rows, list):
        _error(errors, where, "redovi sekcije nisu ispravni.")
        return

    for row_index, row in enumerate(rows):
        _validate_row(row, errors, section_index=section_index, row_index=row_index)


def _validate_section_settings(settings: dict[str, Any], errors: list[str], *, where: str) -> None:
    for key, allowed, label in (
        ("background", _ALLOWED_BACKGROUND, "pozadine"),
        ("container_width", _ALLOWED_CONTAINER, "širine sekcije"),
    ):
        value = settings.get(key)
        if value is not None and value not in allowed:
            _error(errors, where, f"izabrana vrednost {label} nije dozvoljena.")

    background_color = settings.get("background_color")
    if background_color is not None and not isinstance(background_color, str):
        _error(errors, where, "boja pozadine mora biti tekst.")
    elif isinstance(background_color, str) and background_color.strip():
        if not normalize_hex_color(background_color):
            _error(
                errors,
                where,
                "unesite ispravnu hex boju pozadine (npr. #f4f4f5).",
            )


def _validate_row(row: Any, errors: list[str], *, section_index: int, row_index: int) -> None:
    where = _where(section=section_index, row=row_index)
    if not isinstance(row, dict):
        _error(errors, where, "red nije ispravan.")
        return

    row_id = row.get("id")
    if not isinstance(row_id, str) or not row_id.strip():
        _error(errors, where, "redu nedostaje identifikator.")

    settings = row.get("settings")
    if settings is not None and not isinstance(settings, dict):
        _error(errors, where, "podešavanja reda nisu ispravna.")
    elif isinstance(settings, dict):
        valign = settings.get("vertical_align")
        if valign is not None and valign not in _ALLOWED_VERTICAL_ALIGN:
            _error(errors, where, "vertikalno poravnanje nije dozvoljeno.")

    columns = row.get("columns")
    if not isinstance(columns, list) or not columns:
        _error(errors, where, "red mora imati bar jednu kolonu.")
        return

    total_desktop = 0
    for col_index, column in enumerate(columns):
        _validate_column(
            column,
            errors,
            section_index=section_index,
            row_index=row_index,
            column_index=col_index,
        )
        col_settings = column.get("settings") or {}
        width = col_settings.get("width_desktop", 12)
        if isinstance(width, int):
            total_desktop += width

    if total_desktop > 12:
        _error(errors, where, "ukupna širina kolona ne sme biti veća od 12.")


def _validate_column(
    column: Any,
    errors: list[str],
    *,
    section_index: int,
    row_index: int,
    column_index: int,
) -> None:
    where = _where(section=section_index, row=row_index, column=column_index)
    if not isinstance(column, dict):
        _error(errors, where, "kolona nije ispravna.")
        return

    column_id = column.get("id")
    if not isinstance(column_id, str) or not column_id.strip():
        _error(errors, where, "koloni nedostaje identifikator.")

    settings = column.get("settings")
    if settings is not None and not isinstance(settings, dict):
        _error(errors, where, "podešavanja kolone nisu ispravna.")
    elif isinstance(settings, dict):
        for width_key, label in (
            ("width_mobile", "mobilnoj"),
            ("width_tablet", "tablet"),
            ("width_desktop", "desktop"),
        ):
            width = settings.get(width_key)
            if width is not None and (not isinstance(width, int) or width < 1 or width > 12):
                _error(errors, where, f"širina na {label} uređaju mora biti od 1 do 12.")
        align = settings.get("horizontal_align")
        if align is not None and align not in _ALLOWED_ALIGN:
            _error(errors, where, "poravnanje kolone nije dozvoljeno.")

    blocks = column.get("blocks")
    if not isinstance(blocks, list):
        _error(errors, where, "elementi kolone nisu ispravni.")
        return

    for block_index, block in enumerate(blocks):
        _validate_block(
            block,
            errors,
            section_index=section_index,
            row_index=row_index,
            column_index=column_index,
            block_index=block_index,
        )


def _validate_block(
    block: Any,
    errors: list[str],
    *,
    section_index: int,
    row_index: int,
    column_index: int,
    block_index: int,
) -> None:
    where = _where(section=section_index, row=row_index, column=column_index)
    if not isinstance(block, dict):
        _error(errors, where, f"element {block_index + 1} nije ispravan.")
        return

    block_id = block.get("id")
    if not isinstance(block_id, str) or not block_id.strip():
        _error(errors, where, f"elementu {block_index + 1} nedostaje identifikator.")

    block_type = block.get("type")
    if not isinstance(block_type, str) or block_type not in SECTION_BLOCK_TYPES:
        _error(errors, where, f"element {block_index + 1} ima nepoznat tip.")
        return

    label = _BLOCK_LABELS.get(block_type, "Element")
    element_where = f"{where} ({label.lower()})"

    settings = block.get("settings")
    if settings is not None and not isinstance(settings, dict):
        _error(errors, element_where, "podešavanja elementa nisu ispravna.")
    elif isinstance(settings, dict):
        align = settings.get("align")
        if align is not None and align not in _ALLOWED_ALIGN:
            _error(errors, element_where, "poravnanje nije dozvoljeno.")
        width_percent = settings.get("width_percent")
        if width_percent is not None:
            try:
                width_value = int(str(width_percent).strip())
            except (TypeError, ValueError):
                _error(errors, element_where, "širina mora biti ceo broj.")
            else:
                if not MEDIA_WIDTH_PERCENT_MIN <= width_value <= MEDIA_WIDTH_PERCENT_MAX:
                    _error(
                        errors,
                        element_where,
                        f"širina mora biti između {MEDIA_WIDTH_PERCENT_MIN}% i {MEDIA_WIDTH_PERCENT_MAX}%.",
                    )

    attrs = block.get("attrs")
    if attrs is not None and not isinstance(attrs, dict):
        _error(errors, element_where, "sadržaj elementa nije ispravan.")
        return

    attrs = attrs or {}

    if block_type == BlockType.HEADING:
        level = attrs.get("level")
        if level not in {1, 2, 3, 4}:
            _error(errors, element_where, "nivo naslova mora biti od H1 do H4.")
        if not isinstance(attrs.get("text"), str):
            _error(errors, element_where, "tekst naslova nije ispravan.")

    elif block_type == BlockType.TEXT:
        if not isinstance(attrs.get("text"), str):
            _error(errors, element_where, "tekst nije ispravan.")

    elif block_type == BlockType.BUTTON:
        if not isinstance(attrs.get("label"), str):
            _error(errors, element_where, "tekst dugmeta nije ispravan.")
        href = attrs.get("href")
        if not isinstance(href, str):
            _error(errors, element_where, "link dugmeta nije ispravan.")
        elif href.strip() and not _is_safe_href(href):
            _error(errors, element_where, "link dugmeta nije dozvoljen.")

    elif block_type == BlockType.IMAGE:
        src = attrs.get("src") or attrs.get("path") or ""
        if src and not isinstance(src, str):
            _error(errors, element_where, "putanja slike nije ispravna.")
        alt = attrs.get("alt")
        if alt is not None and not isinstance(alt, str):
            _error(errors, element_where, "alt tekst nije ispravan.")
        if isinstance(src, str) and src.strip() and not str(alt or "").strip():
            _error(errors, element_where, "slika mora imati alt tekst.")
        media_asset_id = attrs.get("media_asset_id")
        if media_asset_id is not None and not isinstance(media_asset_id, str):
            _error(errors, element_where, "identifikator medija nije ispravan.")

    elif block_type == BlockType.VIDEO:
        url = str(attrs.get("url") or "").strip()
        media_path = str(attrs.get("path") or attrs.get("src") or "").strip()
        if url and not isinstance(attrs.get("url"), str):
            _error(errors, element_where, "YouTube link nije ispravan.")
        elif url:
            from page.blocks.youtube import is_youtube_url

            if not is_youtube_url(url):
                _error(errors, element_where, "unesite ispravan YouTube link.")
        elif not media_path:
            pass
        elif not isinstance(media_path, str):
            _error(errors, element_where, "putanja video fajla nije ispravna.")
        aspect = (block.get("settings") or {}).get("aspect")
        if aspect is not None and aspect not in {"16:9", "4:3"}:
            _error(errors, element_where, "odnos video snimka mora biti 16:9 ili 4:3.")

    elif block_type == BlockType.FAQ:
        style = attrs.get("style")
        if style not in {"accordion", "list"}:
            _error(errors, element_where, "stil FAQ-a mora biti accordion ili lista.")
        items = attrs.get("items")
        if not isinstance(items, list) or not items:
            _error(errors, element_where, "FAQ mora imati bar jedno pitanje.")
        else:
            for item_index, item in enumerate(items):
                item_label = f"{element_where}, stavka {item_index + 1}"
                if not isinstance(item, dict):
                    _error(errors, item_label, "stavka nije ispravna.")
                    continue
                if not isinstance(item.get("question"), str):
                    _error(errors, item_label, "pitanje nije ispravno.")
                if not isinstance(item.get("answer"), str):
                    _error(errors, item_label, "odgovor nije ispravan.")

    elif block_type == BlockType.DIVIDER:
        return


def is_valid_row_preset(preset: str) -> bool:
    return preset in ROW_PRESETS


def _is_safe_href(href: str) -> bool:
    return is_safe_href(href)

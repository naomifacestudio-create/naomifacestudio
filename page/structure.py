"""Fabrike za structure-first page JSON (section → row → column → block)."""

from __future__ import annotations

from typing import Any

from page.ids import new_block_id, new_column_id, new_row_id, new_section_id

DEFAULT_SECTION_SETTINGS: dict[str, str] = {
    "background": "default",
    "background_color": "",
    "container_width": "contained",
}

DEFAULT_ROW_SETTINGS: dict[str, str] = {
    "vertical_align": "top",
}

DEFAULT_COLUMN_SETTINGS: dict[str, Any] = {
    "width_mobile": 12,
    "width_tablet": 12,
    "width_desktop": 12,
    "horizontal_align": "center",
}

DEFAULT_BLOCK_SETTINGS: dict[str, str] = {
    "align": "center",
}

MEDIA_WIDTH_PERCENT_MIN = 10
MEDIA_WIDTH_PERCENT_MAX = 100

ROW_PRESETS: dict[str, tuple[int, ...]] = {
    "one": (12,),
    "two_equal": (6, 6),
    "two_66_33": (8, 4),
    "two_33_66": (4, 8),
    "three_equal": (4, 4, 4),
}


def default_block_settings() -> dict[str, str]:
    return dict(DEFAULT_BLOCK_SETTINGS)


def normalize_width_percent(settings: dict[str, Any] | None) -> int:
    raw = (settings or {}).get("width_percent", MEDIA_WIDTH_PERCENT_MAX)
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        value = MEDIA_WIDTH_PERCENT_MAX
    return max(MEDIA_WIDTH_PERCENT_MIN, min(MEDIA_WIDTH_PERCENT_MAX, value))


def create_section(*, section_id: str | None = None) -> dict[str, Any]:
    return {
        "id": section_id or new_section_id(),
        "settings": dict(DEFAULT_SECTION_SETTINGS),
        "rows": [create_row(preset="one")],
    }


def create_row(*, preset: str = "one", row_id: str | None = None) -> dict[str, Any]:
    widths = ROW_PRESETS.get(preset, ROW_PRESETS["one"])
    return {
        "id": row_id or new_row_id(),
        "settings": dict(DEFAULT_ROW_SETTINGS),
        "columns": [create_column(width_desktop=width) for width in widths],
    }


def create_column(
    *,
    width_desktop: int = 12,
    width_tablet: int | None = None,
    width_mobile: int = 12,
    column_id: str | None = None,
) -> dict[str, Any]:
    settings = dict(DEFAULT_COLUMN_SETTINGS)
    settings["width_desktop"] = width_desktop
    settings["width_tablet"] = width_tablet if width_tablet is not None else width_desktop
    settings["width_mobile"] = width_mobile
    return {
        "id": column_id or new_column_id(),
        "settings": settings,
        "blocks": [],
    }


def create_heading_block(*, level: int = 2, text: str = "") -> dict[str, Any]:
    return {
        "id": new_block_id(),
        "type": "heading",
        "settings": default_block_settings(),
        "attrs": {"level": level, "text": text or "Naslov"},
    }


def create_text_block(*, text: str = "") -> dict[str, Any]:
    return {
        "id": new_block_id(),
        "type": "text",
        "settings": default_block_settings(),
        "attrs": {"text": text or ""},
    }


def create_divider_block() -> dict[str, Any]:
    return {
        "id": new_block_id(),
        "type": "divider",
        "settings": default_block_settings(),
        "attrs": {},
    }


def create_image_block() -> dict[str, Any]:
    return {
        "id": new_block_id(),
        "type": "image",
        "settings": {**default_block_settings(), "width_percent": "100"},
        "attrs": {
            "src": "",
            "path": "",
            "storage": "",
            "alt": "",
            "caption": "",
            "media_asset_id": "",
        },
    }


def create_video_block() -> dict[str, Any]:
    return {
        "id": new_block_id(),
        "type": "video",
        "settings": {**default_block_settings(), "aspect": "16:9", "width_percent": "100"},
        "attrs": {
            "url": "",
            "path": "",
            "storage": "",
            "src": "",
            "poster": "",
            "poster_path": "",
            "poster_storage": "",
            "caption": "",
        },
    }


def create_faq_block() -> dict[str, Any]:
    return {
        "id": new_block_id(),
        "type": "faq",
        "settings": default_block_settings(),
        "attrs": {
            "style": "accordion",
            "items": [
                {"question": "Prvo pitanje?", "answer": "Odgovor na prvo pitanje."},
                {"question": "Drugo pitanje?", "answer": "Odgovor na drugo pitanje."},
            ],
        },
    }


def create_button_block() -> dict[str, Any]:
    return {
        "id": new_block_id(),
        "type": "button",
        "settings": default_block_settings(),
        "attrs": {"label": "Saznajte više", "href": "", "style": "primary"},
    }


def create_block(block_type: str) -> dict[str, Any]:
    factories = {
        "heading": lambda: create_heading_block(),
        "text": lambda: create_text_block(),
        "divider": create_divider_block,
        "image": create_image_block,
        "video": create_video_block,
        "faq": create_faq_block,
        "button": create_button_block,
    }
    factory = factories.get(block_type)
    if factory is None:
        raise ValueError(f"Nepoznat tip elementa: {block_type}")
    return factory()

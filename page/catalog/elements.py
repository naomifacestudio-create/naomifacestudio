"""Element catalog metadata for structure-first builder."""

from __future__ import annotations

from page.structure import ROW_PRESETS

BUILDER_ELEMENTS = (
    {
        "id": "heading",
        "label": "Naslov",
        "description": "H1–H4 (razina je semantička; veličina i format ručno)",
    },
    {"id": "text", "label": "Tekst", "description": "Paragraf"},
    {"id": "image", "label": "Slika", "description": "Slika s alt tekstom"},
    {"id": "video", "label": "Video", "description": "YouTube video"},
    {"id": "faq", "label": "FAQ", "description": "Pitanja i odgovori"},
    {"id": "button", "label": "Gumb", "description": "CTA poveznica gumba"},
    {"id": "divider", "label": "Linija", "description": "Horizontalna linija"},
)

ROW_PRESET_LABELS = {
    "one": "1 stupac",
    "two_equal": "2 jednaka stupca",
    "two_66_33": "2 stupca (66% / 33%)",
    "two_33_66": "2 stupca (33% / 66%)",
    "three_equal": "3 jednaka stupca",
}


def build_builder_catalog() -> dict:
    return {
        "elements": list(BUILDER_ELEMENTS),
        "row_presets": [
            {"id": preset_id, "label": ROW_PRESET_LABELS.get(preset_id, preset_id)}
            for preset_id in ROW_PRESETS
        ],
        "section_settings": [
            {"id": "background", "label": "Pozadina (preset)", "type": "enum", "options": ["default", "light", "dark", "accent"]},
            {"id": "background_color", "label": "Pozadina (hex)", "type": "text", "placeholder": "#f4f4f5"},
            {"id": "container_width", "label": "Širina", "type": "enum", "options": ["contained", "full"]},
        ],
        "row_settings": [
            {"id": "vertical_align", "label": "Vertikalno", "type": "enum", "options": ["top", "center", "bottom"]},
        ],
        "column_settings": [
            {"id": "horizontal_align", "label": "Poravnanje", "type": "enum", "options": ["left", "center", "right"]},
        ],
        "block_settings": [
            {"id": "align", "label": "Poravnanje", "type": "enum", "options": ["left", "center", "right"]},
        ],
    }

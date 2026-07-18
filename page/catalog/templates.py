"""Katalog section template-a i varijanti."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from page.ids import new_block_id, new_column_id, new_section_id


@dataclass(frozen=True)
class SectionTemplateVariant:
    id: str
    label: str
    layout_id: str
    default_settings: dict[str, Any]
    build_blocks: Callable[[], list[dict[str, Any]]]


@dataclass(frozen=True)
class SectionTemplate:
    id: str
    label: str
    category: str
    description: str
    variants: tuple[SectionTemplateVariant, ...]


def _hero_classic_blocks() -> list[dict[str, Any]]:
    return [
        {
            "id": new_block_id(),
            "type": "heading",
            "zone_id": "hero_content",
            "attrs": {"level": 1, "text": "Naslov stranice"},
        },
        {
            "id": new_block_id(),
            "type": "text",
            "zone_id": "hero_content",
            "attrs": {"text": "Kratak uvodni tekst koji objašnjava sadržaj stranice."},
        },
        {
            "id": new_block_id(),
            "type": "button",
            "zone_id": "hero_actions",
            "attrs": {"label": "Saznajte više", "href": "", "style": "primary"},
        },
    ]


def _cta_light_blocks() -> list[dict[str, Any]]:
    return [
        {
            "id": new_block_id(),
            "type": "heading",
            "zone_id": "cta_content",
            "attrs": {"level": 2, "text": "Spremni za sledeći korak?"},
        },
        {
            "id": new_block_id(),
            "type": "text",
            "zone_id": "cta_content",
            "attrs": {"text": "Kontaktirajte nas i saznajte više o našim uslugama."},
        },
        {
            "id": new_block_id(),
            "type": "button",
            "zone_id": "cta_actions",
            "attrs": {"label": "Kontakt", "href": "/kontakt/", "style": "primary"},
        },
    ]


def _cta_dark_blocks() -> list[dict[str, Any]]:
    return [
        {
            "id": new_block_id(),
            "type": "heading",
            "zone_id": "cta_content",
            "attrs": {"level": 2, "text": "Spremni za sledeći korak?"},
        },
        {
            "id": new_block_id(),
            "type": "text",
            "zone_id": "cta_content",
            "attrs": {"text": "Kontaktirajte nas i saznajte više o našim uslugama."},
        },
        {
            "id": new_block_id(),
            "type": "button",
            "zone_id": "cta_actions",
            "attrs": {"label": "Kontakt", "href": "/kontakt/", "style": "primary"},
        },
    ]


SECTION_TEMPLATES: dict[str, SectionTemplate] = {
    "hero": SectionTemplate(
        id="hero",
        label="Hero",
        category="intro",
        description="Glavna uvodna sekcija stranice.",
        variants=(
            SectionTemplateVariant(
                id="classic",
                label="Klasičan",
                layout_id="one_full",
                default_settings={
                    "container_width": "contained",
                    "background": "default",
                    "text_align": "left",
                },
                build_blocks=_hero_classic_blocks,
            ),
            SectionTemplateVariant(
                id="centered",
                label="Centriran",
                layout_id="one_full",
                default_settings={
                    "container_width": "contained",
                    "background": "default",
                    "text_align": "center",
                },
                build_blocks=_hero_classic_blocks,
            ),
        ),
    ),
    "cta": SectionTemplate(
        id="cta",
        label="CTA",
        category="conversion",
        description="Poziv na akciju na kraju stranice.",
        variants=(
            SectionTemplateVariant(
                id="light",
                label="Svijetla",
                layout_id="one_full",
                default_settings={
                    "container_width": "contained",
                    "background": "light",
                    "text_align": "center",
                },
                build_blocks=_cta_light_blocks,
            ),
            SectionTemplateVariant(
                id="dark",
                label="Tamna",
                layout_id="one_full",
                default_settings={
                    "container_width": "contained",
                    "background": "dark",
                    "text_align": "center",
                },
                build_blocks=_cta_dark_blocks,
            ),
        ),
    ),
}


def get_section_template(template_id: str) -> SectionTemplate | None:
    return SECTION_TEMPLATES.get(template_id)


def get_section_variant(template_id: str, variant_id: str) -> SectionTemplateVariant | None:
    template = get_section_template(template_id)
    if template is None:
        return None
    for variant in template.variants:
        if variant.id == variant_id:
            return variant
    return None


def list_section_templates() -> list[SectionTemplate]:
    return list(SECTION_TEMPLATES.values())

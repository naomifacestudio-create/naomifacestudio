"""Instanciranje section template-a u iv_page_v1 section JSON."""

from __future__ import annotations

from typing import Any

from page.catalog.templates import get_section_template, get_section_variant
from page.ids import new_column_id, new_section_id
from page.layouts import get_layout


class TemplateInstantiationError(ValueError):
    pass


def instantiate_section(
    template_id: str,
    variant_id: str,
    *,
    section_id: str | None = None,
) -> dict[str, Any]:
    template = get_section_template(template_id)
    if template is None:
        raise TemplateInstantiationError(f"Nepoznat template '{template_id}'.")

    variant = get_section_variant(template_id, variant_id)
    if variant is None:
        raise TemplateInstantiationError(
            f"Nepoznata varijanta '{variant_id}' za template '{template_id}'."
        )

    layout = get_layout(variant.layout_id)
    if layout is None:
        raise TemplateInstantiationError(f"Nepoznat layout '{variant.layout_id}'.")

    blocks = variant.build_blocks()
    columns: list[dict[str, Any]] = []
    for layout_column in layout.columns:
        column_blocks = blocks if layout_column.index == 0 else []
        columns.append(
            {
                "id": new_column_id(),
                "index": layout_column.index,
                "blocks": column_blocks,
            }
        )

    return {
        "id": section_id or new_section_id(),
        "template_id": template_id,
        "variant_id": variant_id,
        "template_version": 1,
        "layout_id": variant.layout_id,
        "settings": dict(variant.default_settings),
        "columns": columns,
    }

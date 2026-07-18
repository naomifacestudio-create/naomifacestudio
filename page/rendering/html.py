"""HTML renderer za iv_page_v1 (structure-first)."""

from __future__ import annotations

from typing import Any

from django.template.loader import render_to_string

from page.blocks.registry import render_block_html
from page.normalize import normalize_page
from page.rendering.base import RenderContext
from page.schema import is_supported_page


class HtmlPageRenderer:
    output_format = "html"

    def render(
        self,
        page: dict[str, Any],
        *,
        context: RenderContext | None = None,
    ) -> str:
        if not is_supported_page(page):
            return ""

        render_context = context or RenderContext()
        render_context.extra.setdefault("page_image_index", 0)
        normalized = normalize_page(page)
        sections = []
        for section in normalized.get("sections") or []:
            built = self._build_section_context(section, render_context)
            if built["rows"]:
                sections.append(built)

        if not sections:
            return ""

        return render_to_string(
            "page/page.html",
            {
                "sections": sections,
                "render_context": render_context,
            },
            request=render_context.request,
        )

    def _build_section_context(self, section: dict[str, Any], context: RenderContext) -> dict[str, Any]:
        settings = section.get("settings") or {}
        rows = []
        for row in section.get("rows") or []:
            rows.append(self._build_row_context(row, context))

        return {
            "id": section.get("id"),
            "settings": settings,
            "rows": rows,
            "css_classes": _section_css_classes(settings),
            "inline_style": _section_inline_style(settings),
        }

    def _build_row_context(self, row: dict[str, Any], context: RenderContext) -> dict[str, Any]:
        settings = row.get("settings") or {}
        columns = []
        for column in row.get("columns") or []:
            columns.append(self._build_column_context(column, context))

        return {
            "id": row.get("id"),
            "settings": settings,
            "columns": columns,
            "css_classes": _row_css_classes(settings),
        }

    def _build_column_context(self, column: dict[str, Any], context: RenderContext) -> dict[str, Any]:
        settings = column.get("settings") or {}
        blocks_html = []
        for block in column.get("blocks") or []:
            html = render_block_html(block, context=context)
            if html:
                blocks_html.append(html)

        return {
            "id": column.get("id"),
            "settings": settings,
            "blocks_html": blocks_html,
            "css_classes": _column_css_classes(settings),
        }


def _section_css_classes(settings: dict[str, Any]) -> str:
    from page.rich_text import normalize_hex_color

    container_width = settings.get("container_width", "contained")
    background = settings.get("background", "default")
    custom_color = normalize_hex_color(settings.get("background_color"))

    classes = [
        "iv-page-section",
        f"iv-page-section--width-{container_width}",
    ]
    if custom_color:
        classes.append("iv-page-section--bg-custom")
    else:
        classes.append(f"iv-page-section--bg-{background}")
    return " ".join(filter(None, classes))


def _section_inline_style(settings: dict[str, Any]) -> str:
    from page.rich_text import normalize_hex_color

    color = normalize_hex_color(settings.get("background_color"))
    if not color:
        return ""
    return f"background-color: {color};"


def _row_css_classes(settings: dict[str, Any]) -> str:
    valign = settings.get("vertical_align", "top")
    return f"iv-page-row iv-page-row--align-{valign}"


def _column_css_classes(settings: dict[str, Any]) -> str:
    mobile = settings.get("width_mobile", 12)
    tablet = settings.get("width_tablet", 12)
    desktop = settings.get("width_desktop", 12)
    align = settings.get("horizontal_align", "left")
    return (
        f"iv-page-col col-mobile-{mobile} col-tablet-{tablet} col-desktop-{desktop} "
        f"iv-page-col--align-{align}"
    )

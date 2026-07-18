"""Page renderer factory."""

from __future__ import annotations

from page.blocks.renderers import bootstrap_block_renderers
from page.rendering.html import HtmlPageRenderer

_RENDERERS: dict[str, HtmlPageRenderer] = {}
_BOOTSTRAPPED = False


def _ensure_bootstrapped() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    bootstrap_block_renderers()
    _BOOTSTRAPPED = True


def get_page_renderer(output_format: str = "html") -> HtmlPageRenderer:
    _ensure_bootstrapped()
    if output_format not in _RENDERERS:
        if output_format != "html":
            raise KeyError(f"Nepoznat page renderer format: {output_format}")
        _RENDERERS[output_format] = HtmlPageRenderer()
    return _RENDERERS[output_format]

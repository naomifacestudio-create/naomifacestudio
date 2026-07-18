"""Block renderer registry za iv_page_v1."""

from __future__ import annotations

from typing import Any, Protocol

from page.constants import BlockType


class BlockRenderer(Protocol):
    block_type: str

    def render_html(self, block: dict[str, Any], *, context: Any) -> str: ...

    def extract_plaintext(self, block: dict[str, Any]) -> str: ...


_RENDERERS: dict[str, BlockRenderer] = {}


def register_block_renderer(renderer: BlockRenderer) -> None:
    _RENDERERS[renderer.block_type] = renderer


def get_block_renderer(block_type: str) -> BlockRenderer | None:
    return _RENDERERS.get(block_type)


def render_block_html(block: dict[str, Any], *, context: Any) -> str:
    block_type = block.get("type")
    renderer = get_block_renderer(block_type)
    if renderer is None:
        return ""
    return renderer.render_html(block, context=context)

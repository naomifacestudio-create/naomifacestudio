"""Render context za iv_page_v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class RenderContext:
    request: Any = None
    preview_mode: bool = False
    visible_only: bool = True
    extra: dict[str, Any] = field(default_factory=dict)
    resolve_media_asset_url: Callable[[str], str] | None = None

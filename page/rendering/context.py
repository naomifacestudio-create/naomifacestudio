"""Render context helpers."""

from __future__ import annotations

from page.rendering.base import RenderContext

EXTRA_PAGE_VERSION = "page_version"


def build_render_context_for_post(post, *, request=None, preview_mode=False, visible_only=True):
    if hasattr(post, "get_page_version"):
        page_version = post.get_page_version()
    else:
        page_version = getattr(post, "page_version", 0)
    return RenderContext(
        request=request,
        preview_mode=preview_mode,
        visible_only=visible_only,
        extra={
            EXTRA_PAGE_VERSION: page_version,
        },
    )

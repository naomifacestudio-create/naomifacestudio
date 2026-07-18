"""Block renderer implementacije."""

from __future__ import annotations

from typing import Any

from django.template.loader import render_to_string

from page.blocks.registry import register_block_renderer
from page.constants import BlockType
from page.rendering.base import RenderContext
from page.rich_text import sanitize_inline_html


class HeadingBlockRenderer:
    block_type = BlockType.HEADING

    def render_html(self, block: dict[str, Any], *, context: RenderContext) -> str:
        attrs = block.get("attrs") or {}
        text = sanitize_inline_html(str(attrs.get("text", "")).strip())
        if not text:
            return ""
        level = attrs.get("level", 2)
        if level not in {1, 2, 3, 4}:
            level = 2
        align = _block_align(block)
        return render_to_string(
            "page/blocks/heading.html",
            {
                "level": level,
                "text": text,
                "align": align,
                "render_context": context,
            },
            request=context.request,
        )

    def extract_plaintext(self, block: dict[str, Any]) -> str:
        from page.rich_text import inline_html_to_plaintext

        attrs = block.get("attrs") or {}
        return inline_html_to_plaintext(str(attrs.get("text", "")))


class TextBlockRenderer:
    block_type = BlockType.TEXT

    def render_html(self, block: dict[str, Any], *, context: RenderContext) -> str:
        attrs = block.get("attrs") or {}
        text = sanitize_inline_html(str(attrs.get("text", "")).strip())
        if not text:
            return ""
        align = _block_align(block)
        return render_to_string(
            "page/blocks/text.html",
            {
                "text": text,
                "align": align,
                "render_context": context,
            },
            request=context.request,
        )

    def extract_plaintext(self, block: dict[str, Any]) -> str:
        from page.rich_text import inline_html_to_plaintext

        attrs = block.get("attrs") or {}
        return inline_html_to_plaintext(str(attrs.get("text", "")))


class ButtonBlockRenderer:
    block_type = BlockType.BUTTON

    def render_html(self, block: dict[str, Any], *, context: RenderContext) -> str:
        attrs = block.get("attrs") or {}
        label = str(attrs.get("label", "")).strip()
        href = str(attrs.get("href", "")).strip()
        if not label:
            return ""
        style = attrs.get("style", "primary")
        if style not in {"primary", "secondary"}:
            style = "primary"
        return render_to_string(
            "page/blocks/button.html",
            {
                "label": label,
                "href": href or "#",
                "style": style,
                "align": _block_align(block),
                "render_context": context,
            },
            request=context.request,
        )

    def extract_plaintext(self, block: dict[str, Any]) -> str:
        attrs = block.get("attrs") or {}
        return str(attrs.get("label", "")).strip()


class ImageBlockRenderer:
    block_type = BlockType.IMAGE

    def render_html(self, block: dict[str, Any], *, context: RenderContext) -> str:
        from page.structure import normalize_width_percent

        attrs = block.get("attrs") or {}
        settings = block.get("settings") or {}
        src = _resolve_image_src(attrs, context)
        alt = str(attrs.get("alt", "")).strip()
        caption = str(attrs.get("caption", "")).strip()
        if not src:
            return ""
        align = settings.get("align", "left")
        if align not in {"left", "center", "right"}:
            align = "left"
        explicit_loading = str(attrs.get("loading") or "").strip().lower()
        if explicit_loading in {"eager", "lazy", "auto"}:
            loading = explicit_loading
        else:
            image_index = int(context.extra.get("page_image_index", 0))
            loading = "eager" if image_index == 0 else "lazy"
            context.extra["page_image_index"] = image_index + 1
        return render_to_string(
            "page/blocks/image.html",
            {
                "src": src,
                "alt": alt,
                "caption": caption,
                "width_percent": normalize_width_percent(settings),
                "align": align,
                "loading": loading,
                "render_context": context,
            },
            request=context.request,
        )

    def extract_plaintext(self, block: dict[str, Any]) -> str:
        attrs = block.get("attrs") or {}
        alt = str(attrs.get("alt", "")).strip()
        caption = str(attrs.get("caption", "")).strip()
        return " ".join(part for part in (alt, caption) if part)


class DividerBlockRenderer:
    block_type = BlockType.DIVIDER

    def render_html(self, block: dict[str, Any], *, context: RenderContext) -> str:
        return render_to_string(
            "page/blocks/divider.html",
            {"render_context": context},
            request=context.request,
        )

    def extract_plaintext(self, block: dict[str, Any]) -> str:
        return ""


class VideoBlockRenderer:
    block_type = BlockType.VIDEO

    def render_html(self, block: dict[str, Any], *, context: RenderContext) -> str:
        from page.blocks.youtube import youtube_embed_src
        from page.structure import normalize_width_percent

        attrs = block.get("attrs") or {}
        url = str(attrs.get("url", "")).strip()
        file_src = str(attrs.get("src") or attrs.get("path") or "").strip()
        embed_url = youtube_embed_src(url) if url else ""

        settings = block.get("settings") or {}
        aspect = settings.get("aspect", "16:9")
        if aspect not in {"16:9", "4:3"}:
            aspect = "16:9"
        align = settings.get("align", "left")
        if align not in {"left", "center", "right"}:
            align = "left"

        if not embed_url and not file_src:
            return ""

        if file_src and not file_src.startswith(("http://", "https://", "/")):
            from django.core.files.storage import storages

            file_src = storages["default"].url(file_src)
        elif file_src.startswith("/") and context.request is not None:
            file_src = context.request.build_absolute_uri(file_src)

        poster = str(attrs.get("poster", "")).strip()
        if poster.startswith("/") and context.request is not None:
            poster = context.request.build_absolute_uri(poster)

        return render_to_string(
            "page/blocks/video.html",
            {
                "embed_url": embed_url,
                "file_src": file_src if not embed_url else "",
                "poster": poster if not embed_url else "",
                "caption": str(attrs.get("caption", "")).strip(),
                "aspect_class": aspect.replace(":", "-"),
                "width_percent": normalize_width_percent(settings),
                "align": align,
                "render_context": context,
            },
            request=context.request,
        )

    def extract_plaintext(self, block: dict[str, Any]) -> str:
        attrs = block.get("attrs") or {}
        parts = [
            str(attrs.get("url", "")).strip(),
            str(attrs.get("src", "")).strip(),
            str(attrs.get("caption", "")).strip(),
        ]
        return " ".join(part for part in parts if part)


class FaqBlockRenderer:
    block_type = BlockType.FAQ

    def render_html(self, block: dict[str, Any], *, context: RenderContext) -> str:
        attrs = block.get("attrs") or {}
        style = attrs.get("style", "accordion")
        if style not in {"accordion", "list"}:
            style = "accordion"

        items = []
        for item in attrs.get("items") or []:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question", "")).strip()
            answer = str(item.get("answer", "")).strip()
            if question or answer:
                items.append({"question": question, "answer": answer})

        if not items:
            return ""

        return render_to_string(
            "page/blocks/faq.html",
            {
                "style": style,
                "items": items,
                "render_context": context,
            },
            request=context.request,
        )

    def extract_plaintext(self, block: dict[str, Any]) -> str:
        attrs = block.get("attrs") or {}
        parts = []
        for item in attrs.get("items") or []:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question", "")).strip()
            answer = str(item.get("answer", "")).strip()
            if question:
                parts.append(question)
            if answer:
                parts.append(answer)
        return "\n".join(parts)


def _block_align(block: dict[str, Any]) -> str:
    settings = block.get("settings") or {}
    align = settings.get("align", "center")
    if align not in {"left", "center", "right"}:
        return "center"
    return align


def _resolve_image_src(attrs: dict[str, Any], context: RenderContext) -> str:
    media_asset_id = attrs.get("media_asset_id")
    if media_asset_id and context.resolve_media_asset_url:
        resolved = context.resolve_media_asset_url(str(media_asset_id))
        if resolved:
            return resolved

    path = str(attrs.get("path", "")).strip()
    if path:
        from django.core.files.storage import storages

        return storages["default"].url(path)
    src = str(attrs.get("src", "")).strip()
    if not src:
        return ""
    if src.startswith("/") and context.request is not None:
        return context.request.build_absolute_uri(src)
    return src


def bootstrap_block_renderers() -> None:
    for renderer in (
        HeadingBlockRenderer(),
        TextBlockRenderer(),
        ButtonBlockRenderer(),
        ImageBlockRenderer(),
        DividerBlockRenderer(),
        VideoBlockRenderer(),
        FaqBlockRenderer(),
    ):
        register_block_renderer(renderer)

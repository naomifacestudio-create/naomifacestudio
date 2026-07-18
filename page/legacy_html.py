"""Convert legacy CKEditor HTML into editable visual-builder documents."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse

from django.conf import settings

from page.plaintext import extract_page_plaintext
from page.rich_text import sanitize_inline_html
from page.schema import empty_page
from page.structure import (
    create_heading_block,
    create_image_block,
    create_section,
    create_text_block,
    create_video_block,
)
from page.validation import validate_page_or_raise


_VOID_TAGS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"})
_BLOCK_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "div",
        "figure",
        "figcaption",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "iframe",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "section",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
        "video",
    }
)
_YOUTUBE_HOSTS = frozenset({"youtube.com", "www.youtube.com", "youtu.be", "www.youtu.be", "youtube-nocookie.com", "www.youtube-nocookie.com"})


@dataclass
class _Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["_Node | str"] = field(default_factory=list)


class _TreeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs) -> None:
        node = _Node(tag.lower(), {str(key).lower(): str(value or "") for key, value in attrs})
        self.stack[-1].children.append(node)
        if node.tag not in _VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs) -> None:
        self.handle_starttag(tag, attrs)
        if self.stack[-1].tag == tag.lower() and tag.lower() not in _VOID_TAGS:
            self.stack.pop()

    def handle_endtag(self, tag) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data) -> None:
        if data:
            self.stack[-1].children.append(data)


def _serialize(node: _Node | str) -> str:
    if isinstance(node, str):
        return escape(node)
    attrs = "".join(
        f' {key}="{escape(value, quote=True)}"'
        for key, value in node.attrs.items()
        if key in {"href", "style"}
    )
    inner = "".join(_serialize(child) for child in node.children)
    if node.tag == "br":
        return "<br>"
    return f"<{node.tag}{attrs}>{inner}</{node.tag}>"


def _text(node: _Node | str) -> str:
    """Extract visible text without inventing word breaks between adjacent text nodes."""
    if isinstance(node, str):
        return node
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
            continue
        if child.tag == "br":
            parts.append("\n")
            continue
        piece = _text(child)
        if not piece:
            continue
        if child.tag in _BLOCK_TAGS or child.tag == "root":
            if parts and not parts[-1].endswith("\n"):
                parts.append("\n")
            parts.append(piece)
            if not piece.endswith("\n"):
                parts.append("\n")
        else:
            parts.append(piece)
    value = "".join(parts)
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    return value.strip()


def _find_first(node: _Node, tags: set[str]) -> _Node | None:
    for child in node.children:
        if not isinstance(child, _Node):
            continue
        if child.tag in tags:
            return child
        found = _find_first(child, tags)
        if found:
            return found
    return None


def _find_all(node: _Node, tags: set[str]) -> list[_Node]:
    found: list[_Node] = []
    for child in node.children:
        if not isinstance(child, _Node):
            continue
        if child.tag in tags:
            found.append(child)
        found.extend(_find_all(child, tags))
    return found


def _storage_path(src: str) -> str:
    """Derive a Django storage-relative key while preserving the public URL."""
    if not src or src.startswith("data:"):
        return ""
    parsed_path = unquote(urlparse(src).path or src).replace("\\", "/")
    media_url = str(getattr(settings, "MEDIA_URL", "/media/") or "/media/")
    media_path = urlparse(media_url).path.strip("/")
    cleaned = parsed_path.lstrip("/")
    marker = f"{media_path}/" if media_path else ""
    if marker and marker in cleaned:
        cleaned = cleaned.split(marker, 1)[1]
    for known_prefix in ("uploads/", "page/", "content/", "blogs/", "education/", "treatments/"):
        position = cleaned.find(known_prefix)
        if position >= 0:
            return cleaned[position:]
    return ""


def _alignment(node: _Node) -> str:
    value = " ".join((node.attrs.get("class", ""), node.attrs.get("style", ""))).lower()
    if "right" in value or "float: right" in value:
        return "right"
    if "left" in value or "float: left" in value:
        return "left"
    return "center"


def _width_percent(node: _Node) -> str:
    raw = " ".join((node.attrs.get("width", ""), node.attrs.get("style", "")))
    match = re.search(r"(?:width\s*:\s*)?(\d{1,3})\s*%", raw, re.IGNORECASE)
    if not match:
        return "100"
    return str(max(10, min(100, int(match.group(1)))))


def _image_block(image: _Node, container: _Node | None = None):
    src = image.attrs.get("src", "").strip()
    if not src:
        return None
    block = create_image_block()
    caption_node = _find_first(container, {"figcaption"}) if container else None
    alt = image.attrs.get("alt", "").strip()
    caption = _text(caption_node) if caption_node else ""
    block["attrs"].update(
        {
            "src": src,
            "path": _storage_path(src),
            "alt": alt or caption or "Slika",
            "caption": caption,
        }
    )
    block["settings"]["align"] = _alignment(container or image)
    block["settings"]["width_percent"] = _width_percent(container or image)
    return block


def _video_block(iframe: _Node):
    src = iframe.attrs.get("src", "").strip()
    host = (urlparse(src).hostname or "").lower()
    if not src or host not in _YOUTUBE_HOSTS:
        return None
    block = create_video_block()
    block["attrs"]["url"] = src
    return block


def _uploaded_video_block(video: _Node):
    source = video.attrs.get("src", "").strip()
    if not source:
        source_node = _find_first(video, {"source"})
        source = source_node.attrs.get("src", "").strip() if source_node else ""
    if not source:
        return None
    block = create_video_block()
    path = _storage_path(source)
    poster = video.attrs.get("poster", "").strip()
    block["attrs"].update(
        {
            "src": source,
            "path": path or source,
            "poster": poster,
            "poster_path": _storage_path(poster),
        }
    )
    return block


def _inline_text(children: list[_Node | str]) -> str:
    return sanitize_inline_html("".join(_serialize(child) for child in children))


def _unwrap_media_container(node: _Node, container: _Node, *, heading_level: int | None = None) -> list[dict]:
    """Preserve order of text and images inside wrappers such as linked <a><img></a>."""
    blocks: list[dict] = []
    inline_buffer: list[_Node | str] = []

    def flush_inline() -> None:
        value = _inline_text(inline_buffer)
        inline_buffer.clear()
        if not (value and _text_from_inline(value)):
            return
        if heading_level is not None:
            blocks.append(create_heading_block(level=heading_level, text=value))
        else:
            blocks.append(create_text_block(text=value))

    for child in node.children:
        if isinstance(child, str):
            inline_buffer.append(child)
            continue
        if child.tag == "img":
            flush_inline()
            block = _image_block(child, container)
            if block:
                blocks.append(block)
            continue
        if child.tag in _BLOCK_TAGS:
            flush_inline()
            blocks.extend(_node_blocks(child))
            continue
        if _find_first(child, {"img"}):
            flush_inline()
            blocks.extend(_unwrap_media_container(child, container, heading_level=heading_level))
            continue
        inline_buffer.append(child)
    flush_inline()
    return blocks


def _container_blocks(node: _Node) -> list[dict]:
    """Split a container into editable text/media blocks in source order."""
    blocks: list[dict] = []
    inline_buffer: list[_Node | str] = []

    def flush_inline() -> None:
        value = _inline_text(inline_buffer)
        inline_buffer.clear()
        if value and _text_from_inline(value):
            blocks.append(create_text_block(text=value))

    for child in node.children:
        if isinstance(child, str):
            inline_buffer.append(child)
            continue
        if child.tag == "img":
            flush_inline()
            block = _image_block(child, node)
            if block:
                blocks.append(block)
            continue
        if child.tag not in _BLOCK_TAGS:
            if _find_first(child, {"img"}):
                flush_inline()
                blocks.extend(_unwrap_media_container(child, node))
            else:
                inline_buffer.append(child)
            continue
        flush_inline()
        blocks.extend(_node_blocks(child))
    flush_inline()
    return blocks


def _text_from_inline(value: str) -> str:
    cleaned = re.sub(r"<br\s*/?>", "\n", value or "", flags=re.IGNORECASE)
    return re.sub(r"<[^>]+>", "", cleaned).replace("&nbsp;", " ").replace("\xa0", " ").strip()


def _list_block(node: _Node) -> dict | None:
    items = [_text(child) for child in node.children if isinstance(child, _Node) and child.tag == "li"]
    items = [item for item in items if item]
    if not items:
        return None
    ordered = node.tag == "ol"
    lines = [
        f"{index}. {escape(item)}" if ordered else f"• {escape(item)}"
        for index, item in enumerate(items, start=1)
    ]
    return create_text_block(text="<br>".join(lines))


def _table_block(node: _Node) -> dict | None:
    rows: list[str] = []
    caption = _find_first(node, {"caption"})
    if caption:
        caption_text = _text(caption)
        if caption_text:
            rows.append(caption_text)

    def visit(current: _Node) -> None:
        if current.tag == "caption":
            return
        if current.tag == "tr":
            cells = [
                _text(child)
                for child in current.children
                if isinstance(child, _Node) and child.tag in {"td", "th"}
            ]
            if cells:
                rows.append(" | ".join(cells))
            return
        for child in current.children:
            if isinstance(child, _Node):
                visit(child)

    visit(node)
    return create_text_block(text="<br>".join(escape(row) for row in rows)) if rows else None


def _node_blocks(node: _Node) -> list[dict]:
    if node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = min(4, int(node.tag[1]))
        if _find_first(node, {"img"}):
            return _unwrap_media_container(node, node, heading_level=level)
        value = _inline_text(node.children)
        return [create_heading_block(level=level, text=value)] if _text_from_inline(value) else []
    if node.tag == "img":
        block = _image_block(node)
        return [block] if block else []
    if node.tag == "figure":
        image = _find_first(node, {"img"})
        if image:
            block = _image_block(image, node)
            return [block] if block else []
        return _container_blocks(node)
    if node.tag == "iframe":
        block = _video_block(node)
        return [block] if block else []
    if node.tag == "video":
        block = _uploaded_video_block(node)
        return [block] if block else []
    if node.tag in {"ul", "ol"}:
        block = _list_block(node)
        return [block] if block else []
    if node.tag == "table":
        block = _table_block(node)
        return [block] if block else []
    if node.tag == "hr":
        from page.structure import create_divider_block

        return [create_divider_block()]
    return _container_blocks(node)


def ckeditor_html_to_page(html: str | None) -> dict:
    """Convert CKEditor HTML to a valid builder page without deleting source data."""
    if not (html or "").strip():
        return empty_page()
    parser = _TreeParser()
    parser.feed(html or "")
    parser.close()
    blocks: list[dict] = []
    for child in parser.root.children:
        if isinstance(child, str):
            value = sanitize_inline_html(child)
            if _text_from_inline(value):
                blocks.append(create_text_block(text=value))
        else:
            blocks.extend(_node_blocks(child))
    if not blocks:
        return empty_page()
    section = create_section()
    section["rows"][0]["columns"][0]["blocks"] = blocks
    page = empty_page()
    page["sections"] = [section]
    validate_page_or_raise(page)
    _assert_conversion_integrity(parser.root, page)
    return page


def _page_blocks(page: dict):
    for section in page.get("sections") or []:
        for row in section.get("rows") or []:
            for column in row.get("columns") or []:
                yield from column.get("blocks") or []


def _word_tokens(value: str) -> list[str]:
    return re.findall(r"\w+", value.lower(), flags=re.UNICODE)


def _is_subsequence(expected: list[str], actual: list[str]) -> bool:
    iterator = iter(actual)
    return all(any(candidate == token for candidate in iterator) for token in expected)


def _visible_characters(value: str) -> list[str]:
    """Normalize text while ignoring boundaries introduced by media blocks."""
    return re.findall(r"\w", value.lower(), flags=re.UNICODE)


def _assert_conversion_integrity(root: _Node, page: dict) -> None:
    """Abort migration instead of silently dropping legacy text or media."""
    blocks = list(_page_blocks(page))

    original_images = [
        node.attrs.get("src", "").strip()
        for node in _find_all(root, {"img"})
        if node.attrs.get("src", "").strip()
    ]
    converted_images = [
        str((block.get("attrs") or {}).get("src") or "").strip()
        for block in blocks
        if block.get("type") == "image"
    ]
    missing_images = [src for src in original_images if src not in converted_images]
    if missing_images:
        raise ValueError(
            "CKEditor conversion would omit image(s): " + ", ".join(missing_images)
        )

    original_media = []
    for node in _find_all(root, {"iframe", "video"}):
        src = node.attrs.get("src", "").strip()
        if node.tag == "video" and not src:
            source_node = _find_first(node, {"source"})
            src = source_node.attrs.get("src", "").strip() if source_node else ""
        if src:
            original_media.append(src)
    converted_media = []
    for block in blocks:
        if block.get("type") != "video":
            continue
        attrs = block.get("attrs") or {}
        converted_media.extend(
            str(attrs.get(key) or "").strip() for key in ("url", "src", "path")
        )
    missing_media = [src for src in original_media if src not in converted_media]
    if missing_media:
        raise ValueError(
            "CKEditor conversion would omit embedded media: " + ", ".join(missing_media)
        )

    original_words = _word_tokens(_text(root))
    converted_plaintext = extract_page_plaintext(page)
    converted_words = _word_tokens(converted_plaintext)
    words_preserved = _is_subsequence(original_words, converted_words)
    characters_preserved = _is_subsequence(
        _visible_characters(_text(root)),
        _visible_characters(converted_plaintext),
    )
    if original_words and not words_preserved and not characters_preserved:
        iterator = iter(converted_words)
        missing = next(
            (token for token in original_words if not any(candidate == token for candidate in iterator)),
            original_words[0],
        )
        raise ValueError(
            "CKEditor conversion would omit or reorder visible text "
            f"(first unmatched token: {missing!r})."
        )


def convert_ckeditor_html(html: str | None) -> tuple[dict, str]:
    page = ckeditor_html_to_page(html)
    return page, extract_page_plaintext(page)

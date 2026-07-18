"""Inline HTML sanitization for text blocks."""

from __future__ import annotations

import re
from html import escape, unescape
from html.parser import HTMLParser
from urllib.parse import urlparse

ALLOWED_INLINE_TAGS = frozenset({"b", "strong", "i", "em", "u", "br", "span", "a"})
FONT_SIZE_MIN_PX = 8
FONT_SIZE_MAX_PX = 96
_FONT_SIZE_RE = re.compile(r"font-size:\s*([0-9]+(?:\.[0-9]+)?)px", re.IGNORECASE)
_DISALLOWED_LINK_SCHEMES = frozenset({"javascript", "data", "vbscript"})
_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def normalize_html_entities(value: str) -> str:
    """Dekodira višestruko escape-ovane entitete i pretvara NBSP u običan razmak."""
    normalized = value or ""
    for _ in range(8):
        decoded = unescape(normalized)
        if decoded == normalized:
            break
        normalized = decoded
    return normalized.replace("\xa0", " ")


def normalize_font_size_px(style: str) -> str | None:
    match = _FONT_SIZE_RE.search(style or "")
    if not match:
        return None
    try:
        value = round(float(match.group(1)))
    except (TypeError, ValueError):
        return None
    if value < FONT_SIZE_MIN_PX or value > FONT_SIZE_MAX_PX:
        return None
    return f"{value}px"


def is_safe_href(href: str) -> bool:
    href = (href or "").strip()
    if not href or href.startswith("#") or href.startswith("/"):
        return True
    if href.startswith(("mailto:", "tel:")):
        return True
    parsed = urlparse(href)
    if not parsed.scheme:
        return True
    scheme = parsed.scheme.lower()
    if scheme in _DISALLOWED_LINK_SCHEMES:
        return False
    return scheme in {"http", "https"}


def normalize_hex_color(value: str | None) -> str:
    """Return normalized #RRGGBB/#RGB or empty string if invalid/blank."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    if not raw.startswith("#"):
        raw = f"#{raw}"
    if not _HEX_COLOR_RE.match(raw):
        return ""
    return raw.lower()


class _InlineHTMLSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._open_tags: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag_name = tag.lower()
        attr_map = dict(attrs)
        if tag_name == "a":
            href = str(attr_map.get("href") or "").strip()
            if href and is_safe_href(href):
                self._parts.append(
                    f'<a href="{escape(href, quote=True)}" target="_blank" rel="noopener noreferrer">'
                )
                self._open_tags.append("a")
            return
        if tag_name == "span":
            font_size = normalize_font_size_px(attr_map.get("style", ""))
            if font_size:
                self._parts.append(f'<span style="font-size: {font_size}">')
                self._open_tags.append("span")
            return
        if tag_name in ALLOWED_INLINE_TAGS:
            self._parts.append(f"<{tag_name}>")
            if tag_name != "br":
                self._open_tags.append(tag_name)

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        if tag_name == "br":
            return
        if self._open_tags and self._open_tags[-1] == tag_name:
            self._parts.append(f"</{tag_name}>")
            self._open_tags.pop()

    def handle_data(self, data: str) -> None:
        self._parts.append(escape(normalize_html_entities(data)))

    def get_html(self) -> str:
        while self._open_tags:
            tag_name = self._open_tags.pop()
            self._parts.append(f"</{tag_name}>")
        return "".join(self._parts).strip()


def sanitize_inline_html(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if "<" not in raw:
        return escape(normalize_html_entities(raw))
    parser = _InlineHTMLSanitizer()
    parser.feed(raw)
    parser.close()
    return parser.get_html()


def inline_html_to_plaintext(value: str) -> str:
    from django.utils.html import strip_tags

    return normalize_html_entities(strip_tags(value or "")).strip()

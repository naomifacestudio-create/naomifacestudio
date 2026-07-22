"""Izvlačenje slika iz sadržaja za SEO analizu."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from PIL import Image, UnidentifiedImageError

from page.constants import BlockType as PageBlockType
from seo.helpers import get_image_dimensions

_FILENAME_STEM = re.compile(r"^(.+?)(?:\.[a-z0-9]{2,5})?$", re.I)


@dataclass(frozen=True)
class PageImageEntry:
    source: str
    label: str
    alt_text: str
    filename: str
    basename: str
    width: int | None
    height: int | None
    file_size: int
    format_name: str
    loading: str = ""

    @property
    def has_alt(self) -> bool:
        return bool(self.alt_text.strip())

    @property
    def stem(self) -> str:
        match = _FILENAME_STEM.match(self.basename)
        return (match.group(1) if match else self.basename).lower()


def _text_has_alt(value: str) -> bool:
    return bool((value or "").strip())


def page_has_missing_alt(page_object, *, visible_only: bool = False) -> bool:
    """Brza provera alt teksta bez otvaranja fajlova slika."""
    _ = visible_only
    if page_object is None or not getattr(page_object, "pk", None):
        return False

    should_render_page = getattr(page_object, "should_render_page", None)
    if callable(should_render_page) and should_render_page():
        body_page = getattr(page_object, "body_page", None) or {}
        for section in body_page.get("sections") or []:
            for row in section.get("rows") or []:
                for column in row.get("columns") or []:
                    for block in column.get("blocks") or []:
                        if not isinstance(block, dict) or block.get("type") != PageBlockType.IMAGE:
                            continue
                        attrs = block.get("attrs") or {}
                        src = str(attrs.get("src") or attrs.get("path") or "").strip()
                        alt = str(attrs.get("alt") or "").strip()
                        if src and not alt:
                            return True
        return False

    return False


def _inspect_image_field(image_field) -> tuple[int | None, int | None, int, str]:
    if not image_field or not getattr(image_field, "name", ""):
        return None, None, 0, ""

    width, height = get_image_dimensions(image_field)
    file_size = 0
    format_name = ""

    try:
        file_size = int(image_field.size or 0)
    except Exception:
        file_size = 0

    if width and height:
        return width, height, file_size, format_name

    try:
        image_field.open("rb")
        with Image.open(image_field) as image:
            width, height = image.size
            format_name = (image.format or "").upper()
    except (UnidentifiedImageError, OSError, ValueError):
        pass
    finally:
        if hasattr(image_field, "close"):
            try:
                image_field.close()
            except Exception:
                pass

    return width, height, file_size, format_name


def _entry_from_field(
    *,
    image_field,
    source: str,
    label: str,
    alt_text: str = "",
) -> PageImageEntry | None:
    if not image_field or not getattr(image_field, "name", ""):
        return None

    filename = image_field.name
    basename = os.path.basename(filename)
    width, height, file_size, format_name = _inspect_image_field(image_field)

    return PageImageEntry(
        source=source,
        label=label,
        alt_text=alt_text,
        filename=filename,
        basename=basename,
        width=width,
        height=height,
        file_size=file_size,
        format_name=format_name,
    )


def get_first_page_image_src(page_object) -> str:
    should_render_page = getattr(page_object, "should_render_page", None)
    if not callable(should_render_page) or not should_render_page():
        return ""

    body_page = getattr(page_object, "body_page", None) or {}
    for section in body_page.get("sections") or []:
        for row in section.get("rows") or []:
            for column in row.get("columns") or []:
                for block in column.get("blocks") or []:
                    if not isinstance(block, dict) or block.get("type") != PageBlockType.IMAGE:
                        continue
                    attrs = block.get("attrs") or {}
                    src = str(attrs.get("src") or attrs.get("path") or "").strip()
                    if src:
                        return src
    return ""


def _normalize_loading(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"eager", "lazy", "auto"}:
        return normalized
    return ""


def _assign_loading_defaults(images: list[PageImageEntry]) -> list[PageImageEntry]:
    if not images:
        return images

    result: list[PageImageEntry] = []
    page_image_seen = False
    for entry in images:
        explicit = _normalize_loading(entry.loading)
        if explicit:
            loading = explicit
        elif entry.source == "featured":
            loading = "eager"
        elif entry.source == "page_image":
            loading = "eager" if not page_image_seen else "lazy"
            page_image_seen = True
        else:
            loading = "lazy"
        result.append(
            PageImageEntry(
                source=entry.source,
                label=entry.label,
                alt_text=entry.alt_text,
                filename=entry.filename,
                basename=entry.basename,
                width=entry.width,
                height=entry.height,
                file_size=entry.file_size,
                format_name=entry.format_name,
                loading=loading,
            )
        )
    return result


def collect_page_images_from_body_page(
    page_object,
    body_page: dict,
    *,
    visible_only: bool = False,
) -> list[PageImageEntry]:
    """Prikuplja slike iz prosleđenog body_page JSON-a (live editor stanje)."""
    _ = visible_only
    images: list[PageImageEntry] = []

    featured = getattr(page_object, "featured_image", None)
    featured_entry = _entry_from_field(
        image_field=featured,
        source="featured",
        label="Featured image",
        alt_text=getattr(page_object, "title", "") or "",
    )
    if featured_entry is not None:
        images.append(featured_entry)

    index = 0
    for section in body_page.get("sections") or []:
        for row in section.get("rows") or []:
            for column in row.get("columns") or []:
                for block in column.get("blocks") or []:
                    if not isinstance(block, dict) or block.get("type") != PageBlockType.IMAGE:
                        continue
                    attrs = block.get("attrs") or {}
                    src = str(attrs.get("src") or attrs.get("path") or "").strip()
                    if not src:
                        continue
                    index += 1
                    path = src
                    if "://" in path:
                        path = urlparse(path).path or path
                    basename = os.path.basename(path.split("?")[0].split("#")[0])
                    images.append(
                        PageImageEntry(
                            source="page_image",
                            label=f"Image (visual builder) #{index}",
                            alt_text=str(attrs.get("alt") or "").strip(),
                            filename=src,
                            basename=basename,
                            width=None,
                            height=None,
                            file_size=0,
                            format_name="",
                            loading=_normalize_loading(str(attrs.get("loading") or "")),
                        )
                    )
    return _assign_loading_defaults(images)


def collect_page_images(page_object, *, visible_only: bool = False) -> list[PageImageEntry]:
    _ = visible_only
    if page_object is None or not getattr(page_object, "pk", None):
        return []

    images: list[PageImageEntry] = []

    should_render_page = getattr(page_object, "should_render_page", None)
    if callable(should_render_page) and should_render_page():
        featured = getattr(page_object, "featured_image", None)
        featured_entry = _entry_from_field(
            image_field=featured,
            source="featured",
            label="Featured image",
            alt_text=getattr(page_object, "title", "") or "",
        )
        if featured_entry is not None:
            images.append(featured_entry)

        body_page = getattr(page_object, "body_page", None) or {}
        index = 0
        for section in body_page.get("sections") or []:
            for row in section.get("rows") or []:
                for column in row.get("columns") or []:
                    for block in column.get("blocks") or []:
                        if not isinstance(block, dict) or block.get("type") != PageBlockType.IMAGE:
                            continue
                        attrs = block.get("attrs") or {}
                        src = str(attrs.get("src") or attrs.get("path") or "").strip()
                        if not src:
                            continue
                        index += 1
                        path = src
                        if "://" in path:
                            path = urlparse(path).path or path
                        basename = os.path.basename(path.split("?")[0].split("#")[0])
                        images.append(
                            PageImageEntry(
                                source="page_image",
                                label=f"Image (visual builder) #{index}",
                                alt_text=str(attrs.get("alt") or "").strip(),
                                filename=src,
                                basename=basename,
                                width=None,
                                height=None,
                                file_size=0,
                                format_name="",
                                loading=_normalize_loading(str(attrs.get("loading") or "")),
                            )
                        )
        return _assign_loading_defaults(images)

    featured = getattr(page_object, "featured_image", None)
    featured_entry = _entry_from_field(
        image_field=featured,
        source="featured",
        label="Featured image",
        alt_text=getattr(page_object, "title", "") or "",
    )
    if featured_entry is not None:
        images.append(featured_entry)

    return _assign_loading_defaults(images)

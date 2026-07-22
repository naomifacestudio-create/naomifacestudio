"""Strukturirano izvlačenje sadržaja za SEO analizu ključnih reči."""

from __future__ import annotations

from dataclasses import dataclass, field

from page.seo_content import extract_page_analysis_parts
from seo.content_text import get_content_plain_text, normalize_whitespace
from seo.services import (
    get_seo_fallback_title,
    get_seo_metadata,
    resolve_meta_description,
    resolve_seo_title,
)


@dataclass(frozen=True)
class ContentAnalysisInput:
    article_title: str = ""
    content: str = ""
    seo_title: str = ""
    meta_description: str = ""
    focus_keyword: str = ""
    h1: str = ""
    first_paragraph: str = ""
    url_slug: str = ""
    image_alt_texts: list[str] = field(default_factory=list)
    image_count: int = 0
    images_with_alt: int = 0
    word_count: int = 0


def _empty_analysis_parts() -> dict:
    return {
        "h1": "",
        "first_paragraph": "",
        "content": "",
        "image_alt_texts": [],
        "image_count": 0,
        "images_with_alt": 0,
    }


def _should_use_page_content(content_object) -> bool:
    should_render_page = getattr(content_object, "should_render_page", None)
    if callable(should_render_page):
        return bool(should_render_page())
    return False


def build_content_analysis_input(
    content_object,
    metadata=None,
    *,
    overrides: dict | None = None,
    visible_only: bool = False,
) -> ContentAnalysisInput:
    overrides = overrides or {}
    metadata = metadata if metadata is not None else get_seo_metadata(content_object)

    if content_object is not None and metadata is not None and getattr(metadata, "locale", None):
        from seo.host_adapter import adapt_content_for_seo

        content_object = adapt_content_for_seo(
            content_object, locale=metadata.locale, metadata=metadata
        )

    article_title = overrides.get("article_title") or get_seo_fallback_title(content_object)
    seo_title = overrides.get("seo_title")
    if seo_title is None:
        seo_title = resolve_seo_title(content_object, metadata)

    meta_description = overrides.get("meta_description")
    if meta_description is None:
        meta_description = resolve_meta_description(content_object, metadata)

    focus_keyword = overrides.get("focus_keyword")
    if focus_keyword is None and metadata is not None:
        focus_keyword = metadata.focus_keyword
    focus_keyword = (focus_keyword or "").strip()

    url_slug = overrides.get("url_slug") or getattr(content_object, "slug", "") or ""
    excerpt = overrides.get("excerpt") or getattr(content_object, "excerpt", "") or ""

    if _should_use_page_content(content_object):
        parts = extract_page_analysis_parts(content_object, visible_only=visible_only)
    else:
        parts = _empty_analysis_parts()

    first_paragraph = overrides.get("first_paragraph") or parts["first_paragraph"]
    if not first_paragraph and excerpt:
        first_paragraph = normalize_whitespace(excerpt)

    h1 = overrides.get("h1") or parts["h1"] or article_title

    content = overrides.get("content")
    if content is None:
        full_text = get_content_plain_text(content_object, visible_only=visible_only, max_length=20000)
        if excerpt and excerpt.strip() and excerpt.strip() not in full_text:
            content = normalize_whitespace(f"{excerpt.strip()} {full_text}")
        else:
            content = full_text or parts["content"]

    image_alt_texts = overrides.get("image_alt_texts")
    if image_alt_texts is None:
        image_alt_texts = parts["image_alt_texts"]

    word_count = len(content.split()) if content else 0

    return ContentAnalysisInput(
        article_title=article_title.strip(),
        content=content.strip(),
        seo_title=seo_title.strip(),
        meta_description=meta_description.strip(),
        focus_keyword=focus_keyword,
        h1=h1.strip(),
        first_paragraph=first_paragraph.strip(),
        url_slug=str(url_slug).strip(),
        image_alt_texts=[alt for alt in image_alt_texts if alt],
        image_count=parts.get("image_count", 0),
        images_with_alt=parts.get("images_with_alt", 0),
        word_count=word_count,
    )

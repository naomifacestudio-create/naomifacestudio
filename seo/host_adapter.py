"""Adapt Reflex localized content objects to cement-style flat SEO attrs."""

from __future__ import annotations

from copy import copy

from core.locales import normalize_content_locale
from page.schema import page_has_content


def adapt_content_for_seo(content_object, locale=None, metadata=None):
    """
    Return a shallow copy with cement-like attrs:
    title, slug, excerpt, body_page, body_plaintext, featured_image, should_render_page().

    Attaches `_seo_analysis_metadata` and `_seo_locale` on the wrapper.
    Preserves the original class so `isinstance(..., BlogPost)` still works.
    """
    if content_object is None:
        return None

    if locale is None and metadata is not None:
        locale = getattr(metadata, "locale", None)
    locale = normalize_content_locale(locale) if locale else getattr(
        content_object, "_seo_locale", None
    )

    if (
        getattr(content_object, "_seo_adapted", False)
        and getattr(content_object, "_seo_locale", None) == locale
    ):
        if metadata is not None:
            content_object._seo_analysis_metadata = metadata
        return content_object

    adapted = copy(content_object)
    adapted._seo_adapted = True
    adapted._seo_locale = locale
    adapted._seo_analysis_metadata = metadata

    if hasattr(content_object, "get_title"):
        adapted.title = content_object.get_title(locale) or ""
    if hasattr(content_object, "get_slug"):
        adapted.slug = content_object.get_slug(locale) or getattr(content_object, "slug", "") or ""
    if hasattr(content_object, "get_excerpt"):
        excerpt = content_object.get_excerpt(locale) or ""
        adapted.excerpt = excerpt
        adapted.short_description = excerpt
    else:
        adapted.excerpt = (
            getattr(content_object, "excerpt", None)
            or getattr(content_object, "short_description", None)
            or ""
        )

    if hasattr(content_object, "get_body_page"):
        adapted.body_page = content_object.get_body_page(locale) or {}
    else:
        adapted.body_page = getattr(content_object, "body_page", None) or {}

    if hasattr(content_object, "get_body_plaintext"):
        adapted.body_plaintext = content_object.get_body_plaintext(locale) or ""
    else:
        adapted.body_plaintext = getattr(content_object, "body_plaintext", "") or ""

    # Cement uses featured_image; Reflex uses thumbnail.
    thumbnail = getattr(content_object, "thumbnail", None)
    featured = getattr(content_object, "featured_image", None)
    adapted.featured_image = featured or thumbnail
    if thumbnail and not getattr(adapted, "thumbnail", None):
        adapted.thumbnail = thumbnail

    def should_render_page() -> bool:
        return page_has_content(getattr(adapted, "body_page", None))

    adapted.should_render_page = should_render_page
    return adapted

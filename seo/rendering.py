"""Centralno renderovanje SEO tagova — spajanje podrazumevanih, sadržaja i override vrednosti."""

from __future__ import annotations

from typing import Any

from seo.defaults import get_site_seo_defaults
from seo.canonical import get_canonical_context, normalize_canonical_url

# Polja koja se renderuju u <head> — jedinstven izvor istine protiv duplikata.
RENDERED_SEO_FIELDS = (
    "title",
    "description",
    "canonical",
    "robots",
    "og_type",
    "og_title",
    "og_description",
    "og_url",
    "og_image",
    "og_image_width",
    "og_image_height",
    "twitter_card",
    "twitter_title",
    "twitter_description",
    "twitter_image",
    "article_published_time",
    "article_modified_time",
)

# Prioritet: 1) site defaults → 2) seo_object (SeoMetadata + title/excerpt fallback) → 3) overrides
OVERRIDE_SYNC_MAP = {
    "title": ("og_title", "twitter_title"),
    "description": ("og_description", "twitter_description"),
    "og_title": ("twitter_title",),
    "og_description": ("twitter_description",),
    "og_image": ("twitter_image",),
}


def apply_seo_overrides(seo: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """View-level override ima najviši prioritet."""
    if not overrides:
        return seo

    merged = dict(seo)
    for key, value in overrides.items():
        if value is None or value == "":
            continue
        merged[key] = value

        for synced_key in OVERRIDE_SYNC_MAP.get(key, ()):
            if synced_key not in overrides or not overrides[synced_key]:
                merged[synced_key] = value

    return merged


def normalize_seo_tags(seo: dict[str, Any]) -> dict[str, Any]:
    """Normalizuje vrednosti pre renderovanja — sprečava prazne duplirane tagove."""
    normalized = dict(seo)

    for key in ("title", "description", "og_title", "og_description", "twitter_title", "twitter_description"):
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = value.strip()

    description = normalized.get("description", "")
    if description:
        normalized["description"] = description[:320]

    for key in ("og_description", "twitter_description"):
        value = normalized.get(key, "")
        if value:
            normalized[key] = value[:320]

    if not normalized.get("twitter_image") and normalized.get("og_image"):
        normalized["twitter_image"] = normalized["og_image"]

    if not normalized.get("twitter_card"):
        normalized["twitter_card"] = (
            "summary_large_image"
            if normalized.get("twitter_image") or normalized.get("og_image")
            else "summary"
        )

    canonical = normalized.get("canonical")
    if canonical:
        normalized["canonical"] = normalize_canonical_url(canonical)

    return normalized


def resolve_seo_tags(
    request,
    *,
    seo_object=None,
    og_type: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Dinamički SEO kontekst za šablone.

    Za blog članke:
    - SeoMetadata polja imaju prioritet nad fallback-om
    - Fallback naslov = article.title
    - Fallback opis = article.excerpt (zatim tekst iz buildera)
    """
    if seo_object is not None and hasattr(seo_object, "get_seo_context"):
        resolved_og_type = og_type or "website"
        seo = seo_object.get_seo_context(request, og_type=resolved_og_type)
    else:
        seo = get_site_seo_defaults(request)
        if og_type:
            seo["og_type"] = og_type

    seo = apply_seo_overrides(seo, overrides or {})
    seo = normalize_seo_tags(seo)

    canonical_path = (overrides or {}).get("canonical_path")
    if not canonical_path and seo_object is not None and hasattr(seo_object, "get_absolute_url"):
        canonical_path = seo_object.get_absolute_url()

    seo.update(
        get_canonical_context(
            request,
            canonical_url=seo.get("canonical"),
            canonical_path=canonical_path,
        )
    )

    if seo.get("canonical_is_paginated"):
        robots = str(seo.get("robots", "index, follow"))
        if robots.startswith("index"):
            seo["robots"] = robots.replace("index", "noindex", 1)

    return seo

"""Pomoćnici za statične stranice — prosleđuju seo_overrides render sistemu."""

from django.urls import reverse

from seo.canonical import build_absolute_canonical, resolve_paginated_canonical


def build_static_page_seo(
    request,
    *,
    title,
    description,
    url_name,
    og_type="website",
    url_kwargs=None,
):
    """
    Kreira seo_overrides rečnik za statične Django stranice.
    Kanonski URL se generiše automatski; paginacija (?page=) se normalizuje.
    """
    path = reverse(url_name, kwargs=url_kwargs or None)
    canonical = resolve_paginated_canonical(request, path) if request else None
    if not canonical and request:
        canonical = build_absolute_canonical(path, request)

    return {
        "title": title,
        "description": description,
        "canonical": canonical,
        "canonical_path": path,
        "og_type": og_type,
        "og_title": title,
        "og_description": description,
        "og_url": canonical,
        "twitter_title": title,
        "twitter_description": description,
    }

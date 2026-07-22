"""Kanonski URL — generisanje, paginacija, deduplikacija, višejezična priprema."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from django.conf import settings

DEFAULT_PAGINATION_PARAM = "page"
DEFAULT_STRIP_QUERY_PARAMS = frozenset(
    {
        "page",
        "p",
        "offset",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "gclid",
        "fbclid",
        "mc_cid",
        "mc_eid",
        "ref",
        "source",
    }
)
TRACKING_QUERY_PREFIXES = ("utm_", "mc_")


def get_site_base_url() -> str:
    return getattr(settings, "SITE_BASE_URL", "").strip().rstrip("/")


def get_default_language_code() -> str:
    return getattr(settings, "SEO_CANONICAL_DEFAULT_LANGUAGE", settings.LANGUAGE_CODE)


def get_pagination_param() -> str:
    return getattr(settings, "SEO_CANONICAL_PAGINATION_PARAM", DEFAULT_PAGINATION_PARAM)


def get_strip_query_params() -> frozenset[str]:
    configured = getattr(settings, "SEO_CANONICAL_STRIP_QUERY_PARAMS", None)
    if configured is None:
        return DEFAULT_STRIP_QUERY_PARAMS
    return frozenset(configured)


def normalize_path(path: str) -> str:
    if not path:
        return "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return path


def localize_path(path: str, language_code: str | None = None) -> str:
    """
    Priprema putanju za buduće višejezične URL-ove.
    Kada SEO_CANONICAL_LANGUAGE_PREFIX=False (podrazumevano), prefiks se ne dodaje.
    """
    path = normalize_path(path)
    if not getattr(settings, "SEO_CANONICAL_LANGUAGE_PREFIX", False):
        return path

    language_code = language_code or get_default_language_code()
    default_language = get_default_language_code()
    prefix = language_code.lower().replace("_", "-")

    if prefix == default_language.lower().replace("_", "-"):
        return path

    if path == "/":
        return f"/{prefix}/"
    return f"/{prefix}{path}"


def _should_strip_query_param(key: str, strip_params: frozenset[str]) -> bool:
    lowered = key.lower()
    if lowered in strip_params:
        return True
    return any(lowered.startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES)


def strip_duplicate_query_params(url: str, *, keep_params: frozenset[str] | None = None) -> str:
    """Uklanja paginaciju, UTM i druge parametre koji stvaraju dupli sadržaj."""
    parsed = urlparse(url)
    if not parsed.query:
        return url

    keep = keep_params or frozenset()
    strip_params = get_strip_query_params()
    filtered = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=False)
        if key in keep or not _should_strip_query_param(key, strip_params)
    ]
    query = urlencode(filtered, doseq=True)
    return urlunparse(parsed._replace(query=query))


def normalize_canonical_url(url: str) -> str:
    """Normalizuje apsolutni kanonski URL."""
    parsed = urlparse(url.strip())
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc
    path = normalize_path(parsed.path or "/")
    cleaned = urlunparse((scheme, netloc, path, "", "", ""))
    return strip_duplicate_query_params(cleaned)


def build_absolute_canonical(
    path_or_url: str | None,
    request=None,
    *,
    language_code: str | None = None,
) -> str | None:
    """Gradi apsolutni kanonski URL — SITE_BASE_URL ima prioritet nad request hostom."""
    if not path_or_url:
        return None

    if path_or_url.startswith(("http://", "https://")):
        return normalize_canonical_url(path_or_url)

    path = localize_path(path_or_url, language_code)
    base = get_site_base_url()
    if base:
        return normalize_canonical_url(urljoin(f"{base}/", path.lstrip("/")))

    if request:
        return normalize_canonical_url(request.build_absolute_uri(path))

    return None


def detect_pagination_page(request) -> int | None:
    """Vraća broj strane (>1) ako je URL paginiran, inače None."""
    if request is None:
        return None

    raw_value = request.GET.get(get_pagination_param(), "").strip()
    if not raw_value.isdigit():
        return None

    page_number = int(raw_value)
    if page_number <= 1:
        return None
    return page_number


def resolve_paginated_canonical(
    request,
    base_path: str,
    *,
    language_code: str | None = None,
) -> str | None:
    """
    Kanonski URL za paginirane liste — uvek prva strana (bez ?page=).
    Sprečava dupli sadržaj između /blog/?page=2 i /blog/.
    """
    canonical = build_absolute_canonical(base_path, request, language_code=language_code)
    if not canonical:
        return None

    if detect_pagination_page(request) is None:
        return canonical

    return normalize_canonical_url(canonical)


def resolve_content_canonical(
    content_object,
    request=None,
    metadata=None,
    *,
    language_code: str | None = None,
) -> str | None:
    """
    Kanonski URL za članak ili CMS stranicu.
    Prioritet: ručni unos u adminu → javna putanja objekta.
    """
    if metadata is not None and getattr(metadata, "canonical_url", "").strip():
        return normalize_canonical_url(metadata.canonical_url.strip())

    if content_object is None:
        return None

    path = None
    if hasattr(content_object, "get_absolute_url"):
        path = content_object.get_absolute_url()

    return build_absolute_canonical(path, request, language_code=language_code)


def resolve_request_canonical(
    request,
    *,
    path: str | None = None,
    language_code: str | None = None,
) -> str | None:
    """Kanonski URL za statične stranice bez seo_object."""
    if request is None:
        return None

    canonical_path = path or request.path
    return resolve_paginated_canonical(
        request,
        canonical_path,
        language_code=language_code,
    )


def get_hreflang_alternates(
    request,
    canonical_path: str,
    *,
    language_code: str | None = None,
) -> list[dict[str, str]]:
    """
    hreflang alternate linkovi za buduće višejezične URL-ove.
    Aktivno samo kada je SEO_HREFLANG_ENABLED=True.
    """
    if not getattr(settings, "SEO_HREFLANG_ENABLED", False):
        return []

    alternates: list[dict[str, str]] = []
    languages = getattr(settings, "LANGUAGES", ())

    for code, _label in languages:
        url = build_absolute_canonical(
            canonical_path,
            request,
            language_code=code,
        )
        if not url:
            continue
        hreflang = code.lower().replace("_", "-")
        alternates.append({"hreflang": hreflang, "url": url})

    default_url = build_absolute_canonical(
        canonical_path,
        request,
        language_code=language_code or get_default_language_code(),
    )
    if default_url:
        alternates.append({"hreflang": "x-default", "url": default_url})

    return alternates


def get_canonical_context(
    request,
    *,
    canonical_url: str | None,
    canonical_path: str | None = None,
    language_code: str | None = None,
) -> dict[str, object]:
    """Dopunski SEO kontekst za paginaciju i hreflang."""
    pagination_page = detect_pagination_page(request)
    path = canonical_path or (urlparse(canonical_url).path if canonical_url else None)

    context: dict[str, object] = {
        "canonical": canonical_url,
        "canonical_is_paginated": pagination_page is not None,
        "canonical_pagination_page": pagination_page,
        "hreflang_alternates": [],
    }

    if path:
        context["hreflang_alternates"] = get_hreflang_alternates(
            request,
            path,
            language_code=language_code,
        )

    return context

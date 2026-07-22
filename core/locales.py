"""Shared content/SEO locale maps for the visual builder stack."""

CONTENT_LOCALES = ("hr", "en")
DEFAULT_CONTENT_LOCALE = "hr"

LOCALE_SUFFIX = {
    "hr": "_hr",
    "en": "_en",
}

LOCALE_LABELS = {
    "hr": "Hrvatski",
    "en": "Engleski",
}

# One SEO profile per content locale.
SEO_LOCALES = CONTENT_LOCALES

BODY_PAGE_FIELDS = tuple(f"body_page{suffix}" for suffix in LOCALE_SUFFIX.values())


def normalize_content_locale(locale=None):
    from django.utils import translation

    locale = locale or translation.get_language() or DEFAULT_CONTENT_LOCALE
    normalized = str(locale).lower().replace("_", "-")
    if normalized.startswith("en"):
        return "en"
    # Treat leftover Serbian cookies/locales as Croatian after the locale restore.
    if normalized.startswith(("hr", "sr")):
        return "hr"
    base = normalized.split("-")[0]
    return base if base in LOCALE_SUFFIX else DEFAULT_CONTENT_LOCALE


def seo_locale_for(locale=None):
    """Map a content locale to its SEO profile locale (1:1)."""
    return normalize_content_locale(locale)

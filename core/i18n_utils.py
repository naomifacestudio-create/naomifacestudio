"""Helpers for models that store parallel sr/en fields (Serbian Latin + English)."""

DEFAULT_CONTENT_LANGUAGE = 'sr'
DEFAULT_DJANGO_LANGUAGE = 'sr-latn'


def active_django_language(language_code=None):
    """
    Resolve a Django locale code from LANGUAGES (``sr-latn`` / ``en``).
    """
    if language_code is None:
        from django.utils.translation import get_language

        language_code = get_language() or DEFAULT_DJANGO_LANGUAGE

    normalized = str(language_code).lower().replace('_', '-')
    if normalized.startswith('en'):
        return 'en'
    if normalized.startswith('sr'):
        return DEFAULT_DJANGO_LANGUAGE
    return DEFAULT_DJANGO_LANGUAGE


def active_language_code(language_code=None):
    """
    Resolve the content-field language code used by bilingual models.

    Django locale codes may be ``sr-latn`` / ``sr_Latn`` / ``sr``; content fields
    use the short ``sr`` / ``en`` suffixes.
    """
    if language_code is None:
        from django.utils.translation import get_language

        language_code = get_language() or DEFAULT_DJANGO_LANGUAGE

    normalized = str(language_code).lower().replace('_', '-')
    if normalized.startswith('en'):
        return 'en'
    if normalized.startswith('sr'):
        return 'sr'
    return DEFAULT_CONTENT_LANGUAGE

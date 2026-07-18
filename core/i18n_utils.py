"""Helpers for models that store parallel hr/en fields (Croatian + English)."""

DEFAULT_CONTENT_LANGUAGE = 'hr'
DEFAULT_DJANGO_LANGUAGE = 'hr'


def active_django_language(language_code=None):
    """
    Resolve a Django locale code from LANGUAGES (``hr`` / ``en``).
    """
    if language_code is None:
        from django.utils.translation import get_language

        language_code = get_language() or DEFAULT_DJANGO_LANGUAGE

    normalized = str(language_code).lower().replace('_', '-')
    if normalized.startswith('en'):
        return 'en'
    # Treat leftover Serbian cookies/locales as Croatian after the locale restore.
    if normalized.startswith(('hr', 'sr')):
        return DEFAULT_DJANGO_LANGUAGE
    return DEFAULT_DJANGO_LANGUAGE


def active_language_code(language_code=None):
    """
    Resolve the content-field language code used by bilingual models.

    Content fields use the ``hr`` / ``en`` suffixes.
    """
    if language_code is None:
        from django.utils.translation import get_language

        language_code = get_language() or DEFAULT_DJANGO_LANGUAGE

    normalized = str(language_code).lower().replace('_', '-')
    if normalized.startswith('en'):
        return 'en'
    # Treat leftover Serbian cookies/locales as Croatian after the locale restore.
    if normalized.startswith(('hr', 'sr')):
        return 'hr'
    return DEFAULT_CONTENT_LANGUAGE

"""Helpers for models that store parallel hr/en fields."""


def active_language_code(language_code=None):
    """
    Resolve the two-letter language code for content fields.

    When ``language_code`` is omitted (e.g. ``{{ blog.get_title }}`` in a template),
    use Django's active locale from ``LocaleMiddleware`` / ``get_language()``.
    """
    if language_code is not None:
        return language_code[:2]
    from django.utils.translation import get_language

    lang = get_language() or 'hr'
    return lang[:2] if len(lang) >= 2 else lang

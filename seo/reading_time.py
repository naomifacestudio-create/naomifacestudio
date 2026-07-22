"""Procena vremena čitanja — za prikaz i schema.org."""

from __future__ import annotations

DEFAULT_WORDS_PER_MINUTE = 200


def count_words(text: str) -> int:
    return len((text or "").split())


def reading_time_minutes(word_count: int, *, words_per_minute: int = DEFAULT_WORDS_PER_MINUTE) -> int:
    if word_count <= 0:
        return 1
    return max(1, round(word_count / words_per_minute))


def reading_time_for_content_object(content_object, *, words_per_minute: int = DEFAULT_WORDS_PER_MINUTE) -> int:
    from seo.content_analysis import build_content_analysis_input

    analysis = build_content_analysis_input(content_object)
    return reading_time_minutes(analysis.word_count, words_per_minute=words_per_minute)


def iso_duration_minutes(minutes: int) -> str:
    """Schema.org timeRequired, npr. PT8M."""
    return f"PT{max(1, minutes)}M"

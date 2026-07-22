"""SEO i čitljivost — Yoast-style ocene (0–100)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResolvedSeoScores:
    title: str
    description: str
    focus_keyword: str
    canonical: str
    og_image: str
    twitter_image: str
    robots_index: bool


def compute_seo_score(
    resolved: ResolvedSeoScores,
    *,
    content_object=None,
    metadata=None,
    request=None,
) -> int:
    """
    Ukupna SEO ocena — delegira na unified scoring engine kada postoji sadržaj.
    `resolved` se zadržava radi kompatibilnosti sa starijim pozivima.
    """
    if content_object is not None:
        from seo.unified_scoring import compute_unified_seo_score

        return compute_unified_seo_score(
            content_object,
            metadata,
            request=request,
            visible_only=False,
        )

    score = 0
    title = resolved.title.strip()
    title_len = len(title)
    if 50 <= title_len <= 60:
        score += 25
    elif 40 <= title_len <= 70:
        score += 15
    elif title:
        score += 5

    description = resolved.description.strip()
    desc_len = len(description)
    if 120 <= desc_len <= 160:
        score += 25
    elif 80 <= desc_len <= 200:
        score += 15
    elif description:
        score += 5

    focus = resolved.focus_keyword.strip().lower()
    if focus:
        if focus in title.lower():
            score += 15
        if focus in description.lower():
            score += 15

    if resolved.og_image or resolved.twitter_image:
        score += 10

    if resolved.robots_index:
        score += 10

    if resolved.canonical:
        score += 10

    return min(score, 100)


def compute_readability_score(content_object, *, visible_only=True) -> int:
    from seo.readability_analyzer import analyze_readability_for_object

    result = analyze_readability_for_object(content_object, visible_only=visible_only)
    return result.score

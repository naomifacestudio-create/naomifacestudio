"""Yoast-style preporuke za interne linkove između blog članaka."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import StrEnum

from blogs.models import BlogPost
from seo.content_analysis import build_content_analysis_input
from seo.content_text import normalize_whitespace
from seo.cornerstone import CORNERSTONE_LINK_BOOST, CORNERSTONE_SORT_PRIORITY
from seo.internal_linking_content import (
    ArticleLinkTarget,
    InternalLink,
    build_article_link_index,
    extract_internal_links_from_object,
    href_matches_post_slug,
    resolve_linked_post_ids,
)
from seo.keyword_analyzer import CheckStatus, keyword_in_text

GENERIC_ANCHORS = {
    "klikni",
    "kliknite",
    "ovde",
    "ovdje",
    "više",
    "vise",
    "čitaj",
    "citaj",
    "pročitaj",
    "procitaj",
    "saznaj",
    "link",
    "ovaj link",
    "ovaj članak",
    "ovaj clanak",
    "detaljnije",
    "pogledaj",
    "klik",
    "here",
    "read more",
}

STOPWORDS = {
    "i",
    "u",
    "na",
    "za",
    "se",
    "je",
    "su",
    "od",
    "do",
    "sa",
    "kao",
    "ili",
    "ali",
    "to",
    "ta",
    "te",
    "bi",
    "ne",
    "da",
    "a",
    "o",
    "iz",
    "po",
    "kod",
    "pri",
}


@dataclass(frozen=True)
class InternalLinkingCheck:
    check_id: str
    label: str
    status: CheckStatus
    message: str
    points: int
    max_points: int


@dataclass(frozen=True)
class LinkSuggestion:
    target_post_id: int
    target_title: str
    target_url: str
    suggested_anchor: str
    match_phrase: str
    reason: str
    relatedness_score: float
    already_linked: bool
    is_cornerstone: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InternalLinkingResult:
    score: int = 0
    checks: list[InternalLinkingCheck] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    link_suggestions: list[LinkSuggestion] = field(default_factory=list)
    existing_links: list[dict] = field(default_factory=list)
    internal_link_count: int = 0
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "checks": [
                {
                    **asdict(check),
                    "status": check.status.value,
                }
                for check in self.checks
            ],
            "recommendations": self.recommendations,
            "link_suggestions": [item.to_dict() for item in self.link_suggestions],
            "existing_links": self.existing_links,
            "internal_link_count": self.internal_link_count,
            "message": self.message,
        }


def _content_tokens(text: str) -> set[str]:
    words = re.findall(r"[\w\u0100-\u024F]+", normalize_whitespace(text).lower())
    return {word for word in words if len(word) > 2 and word not in STOPWORDS}


def _is_generic_anchor(anchor: str) -> bool:
    normalized = normalize_whitespace(anchor).lower()
    if not normalized:
        return True
    if normalized in GENERIC_ANCHORS:
        return True
    return len(normalized.split()) <= 1 and len(normalized) <= 4


def _short_title(title: str, *, max_words: int = 5) -> str:
    words = normalize_whitespace(title).split()
    if len(words) <= max_words:
        return title.strip()
    return " ".join(words[:max_words])


def _find_phrase_in_content(content: str, phrases: tuple[str, ...]) -> str:
    ranked = sorted(phrases, key=lambda phrase: len(phrase.split()), reverse=True)
    for phrase in ranked:
        if keyword_in_text(phrase, content):
            return phrase
    return ""


def _suggest_anchor(content: str, target: ArticleLinkTarget) -> tuple[str, str, str]:
    match_phrase = _find_phrase_in_content(content, target.link_phrases)
    if match_phrase:
        return match_phrase, match_phrase, "Phrase already appears in the text — ideal anchor text."

    if target.focus_keyword:
        return target.focus_keyword, "", "Use the target post focus keyword as the anchor."

    short_title = _short_title(target.title)
    return short_title, "", "Use the shortened target post title as anchor text."


def _compute_relatedness_score(
    *,
    content: str,
    source_category_id: int | None,
    source_tokens: set[str],
    target: ArticleLinkTarget,
) -> tuple[float, str]:
    score = 0.0
    reasons: list[str] = []

    for phrase in target.link_phrases:
        if keyword_in_text(phrase, content):
            score += 4.0 + len(phrase.split())
            reasons.append(f'phrase match "{phrase}"')
            break

    if source_category_id and source_category_id == target.category_id:
        score += 10.0
        reasons.append("same category")

    target_tokens = _content_tokens(" ".join(target.link_phrases))
    overlap = len(source_tokens & target_tokens)
    if overlap:
        score += min(overlap * 1.5, 12.0)
        reasons.append(f"{overlap} shared terms")

    if target.is_cornerstone:
        score += CORNERSTONE_LINK_BOOST
        reasons.append("cornerstone post — priority")

    if target.focus_keyword and keyword_in_text(target.focus_keyword, content):
        score += 8.0
        if f'focus "{target.focus_keyword}"' not in reasons:
            reasons.append(f'focus "{target.focus_keyword}"')

    reason = ", ".join(dict.fromkeys(reasons)) or "semantic closeness of titles and keywords"
    return score, reason


def _build_link_suggestions(
    *,
    content: str,
    source_category_id: int | None,
    targets: list[ArticleLinkTarget],
    linked_post_ids: set[int],
    limit: int = 8,
) -> list[LinkSuggestion]:
    source_tokens = _content_tokens(content)
    scored: list[tuple[float, str, ArticleLinkTarget]] = []

    for target in targets:
        score, reason = _compute_relatedness_score(
            content=content,
            source_category_id=source_category_id,
            source_tokens=source_tokens,
            target=target,
        )
        if score <= 0:
            continue
        scored.append((score, reason, target))

    scored.sort(
        key=lambda item: (
            item[0] + (CORNERSTONE_SORT_PRIORITY if item[2].is_cornerstone else 0),
            item[0],
        ),
        reverse=True,
    )

    suggestions: list[LinkSuggestion] = []
    for score, reason, target in scored[:limit]:
        anchor, match_phrase, anchor_reason = _suggest_anchor(content, target)
        suggestions.append(
            LinkSuggestion(
                target_post_id=target.post_id,
                target_title=target.title,
                target_url=target.url_path,
                suggested_anchor=anchor,
                match_phrase=match_phrase,
                reason=f"{reason.capitalize()}. {anchor_reason}",
                relatedness_score=round(score, 1),
                already_linked=target.post_id in linked_post_ids,
                is_cornerstone=target.is_cornerstone,
            )
        )

    return suggestions


def _score_checks(
    *,
    links: list[InternalLink],
    suggestions: list[LinkSuggestion],
    targets: list[ArticleLinkTarget],
    linked_post_ids: set[int],
    source_category_id: int | None,
) -> tuple[list[InternalLinkingCheck], int]:
    checks: list[InternalLinkingCheck] = []
    link_count = len(links)

    if link_count == 0:
        count_status = CheckStatus.BAD
        count_message = "No internal links to other posts — add 2–5 relevant links."
        count_points = 0
    elif link_count == 1:
        count_status = CheckStatus.OK
        count_message = "There is 1 internal link — add 1–3 more relevant links."
        count_points = 12
    elif 2 <= link_count <= 5:
        count_status = CheckStatus.GOOD
        count_message = f"Internal link count ({link_count}) is within the recommended range."
        count_points = 20
    else:
        count_status = CheckStatus.OK
        count_message = f"You have {link_count} internal links — check they are not too dense."
        count_points = 14

    checks.append(
        InternalLinkingCheck(
            check_id="internal_link_count",
            label="Broj internih linkova",
            status=count_status,
            message=count_message,
            points=count_points,
            max_points=20,
        )
    )

    descriptive = [link for link in links if not _is_generic_anchor(link.anchor_text)]
    if not links:
        anchor_status = CheckStatus.NEUTRAL
        anchor_message = "No links to check anchor text."
        anchor_points = 8
    elif len(descriptive) == len(links):
        anchor_status = CheckStatus.GOOD
        anchor_message = "All anchor texts are descriptive and relevant."
        anchor_points = 20
    elif descriptive:
        anchor_status = CheckStatus.OK
        anchor_message = (
            f"{len(descriptive)}/{len(links)} links have descriptive anchor text — "
            'avoid "click here" and similar generic phrases.'
        )
        anchor_points = 12
    else:
        anchor_status = CheckStatus.BAD
        anchor_message = "Anchor texts are too generic — use keywords or post titles."
        anchor_points = 0

    checks.append(
        InternalLinkingCheck(
            check_id="anchor_text_quality",
            label="Kvalitet anchor teksta",
            status=anchor_status,
            message=anchor_message,
            points=anchor_points,
            max_points=20,
        )
    )

    actionable = [item for item in suggestions if not item.already_linked]
    fulfilled = [item for item in suggestions if item.already_linked]
    if not suggestions:
        opp_status = CheckStatus.NEUTRAL
        opp_message = "Not enough published posts for linking suggestions."
        opp_points = 10
    elif not actionable:
        opp_status = CheckStatus.GOOD
        opp_message = "You already linked the top recommended posts."
        opp_points = 25
    else:
        ratio = len(fulfilled) / max(len(suggestions), 1)
        if ratio >= 0.6:
            opp_status = CheckStatus.GOOD
            opp_message = f"Used {len(fulfilled)}/{len(suggestions)} top suggestions."
            opp_points = 22
        elif ratio >= 0.3:
            opp_status = CheckStatus.OK
            opp_message = f"Linked {len(fulfilled)}/{len(suggestions)} recommended posts."
            opp_points = 14
        else:
            opp_status = CheckStatus.BAD
            opp_message = f"Missing {len(actionable)} recommended internal links."
            opp_points = 4

    checks.append(
        InternalLinkingCheck(
            check_id="recommendation_coverage",
            label="Suggestions used",
            status=opp_status,
            message=opp_message,
            points=opp_points,
            max_points=25,
        )
    )

    cornerstones = [
        target
        for target in targets
        if target.is_cornerstone
        and (source_category_id is None or target.category_id == source_category_id)
    ]
    if not cornerstones:
        corner_status = CheckStatus.NEUTRAL
        corner_message = "No cornerstone posts in the same category."
        corner_points = 10
    else:
        linked_cornerstone = any(target.post_id in linked_post_ids for target in cornerstones)
        if linked_cornerstone:
            corner_status = CheckStatus.GOOD
            corner_message = "Post is linked to cornerstone content."
            corner_points = 15
        else:
            corner_status = CheckStatus.BAD
            corner_message = "Add a link to a cornerstone post on the same topic."
            corner_points = 0

    checks.append(
        InternalLinkingCheck(
            check_id="cornerstone_link",
            label="Cornerstone linking",
            status=corner_status,
            message=corner_message,
            points=corner_points,
            max_points=15,
        )
    )

    body_links = [link for link in links if link.source == "html"]
    if not links:
        distribution_status = CheckStatus.NEUTRAL
        distribution_message = "No internal links in the body text."
        distribution_points = 8
    elif body_links:
        distribution_status = CheckStatus.GOOD
        distribution_message = (
            f"{len(body_links)} link(s) in the text — good contextual linking."
        )
        distribution_points = 20
    else:
        distribution_status = CheckStatus.OK
        distribution_message = "Links are only in buttons/images — add contextual links in the text."
        distribution_points = 10

    checks.append(
        InternalLinkingCheck(
            check_id="link_distribution",
            label="Linkovi u tekstu",
            status=distribution_status,
            message=distribution_message,
            points=distribution_points,
            max_points=20,
        )
    )

    total_points = sum(check.points for check in checks)
    max_total = sum(check.max_points for check in checks)
    score = round((total_points / max_total) * 100) if max_total else 0
    return checks, score


def _build_recommendations(
    checks: list[InternalLinkingCheck],
    suggestions: list[LinkSuggestion],
) -> list[str]:
    recommendations: list[str] = []

    for check in checks:
        if check.status == CheckStatus.BAD:
            recommendations.append(check.message)

    for suggestion in suggestions:
        if suggestion.already_linked:
            continue
        prefix = "[Cornerstone] " if suggestion.is_cornerstone else ""
        recommendations.append(
            f'{prefix}Link "{suggestion.suggested_anchor}" to the post "{suggestion.target_title}".'
        )

    if not recommendations:
        recommendations.append("Great job — internal links are well optimized.")

    return recommendations[:12]


def analyze_internal_linking(
    content_object,
    metadata=None,
    *,
    overrides: dict | None = None,
    visible_only: bool = False,
) -> InternalLinkingResult:
    if not isinstance(content_object, BlogPost):
        return InternalLinkingResult(
            score=0,
            message="Internal links are analyzed for blog posts only.",
        )

    analysis_input = build_content_analysis_input(
        content_object,
        metadata,
        overrides=overrides,
        visible_only=visible_only,
    )
    content = analysis_input.content
    if not content.strip():
        return InternalLinkingResult(
            score=0,
            message="Add content in the builder to get internal link suggestions.",
        )

    links = extract_internal_links_from_object(content_object, visible_only=visible_only)
    targets = build_article_link_index(exclude_pk=content_object.pk)
    linked_post_ids = resolve_linked_post_ids(links, targets)

    suggestions = _build_link_suggestions(
        content=content,
        source_category_id=getattr(content_object, "category_id", None),
        targets=targets,
        linked_post_ids=linked_post_ids,
    )

    checks, score = _score_checks(
        links=links,
        suggestions=suggestions,
        targets=targets,
        linked_post_ids=linked_post_ids,
        source_category_id=getattr(content_object, "category_id", None),
    )

    existing_links = [
        {
            "href": link.href,
            "anchor_text": link.anchor_text or "—",
            "source": link.source,
            "target_slug": next(
                (
                    target.slug
                    for target in targets
                    if href_matches_post_slug(link.href, target.slug)
                ),
                "",
            ),
        }
        for link in links
    ]

    return InternalLinkingResult(
        score=score,
        checks=checks,
        recommendations=_build_recommendations(checks, suggestions),
        link_suggestions=suggestions,
        existing_links=existing_links,
        internal_link_count=len(links),
    )

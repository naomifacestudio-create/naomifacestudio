"""Unified SEO scoring engine — agregirana score i machine-readable izlaz."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from blogs.models import BlogPost
from seo.content_analysis import ContentAnalysisInput, build_content_analysis_input
from seo.internal_linking import analyze_internal_linking
from seo.keyword_analyzer import (
    CheckStatus,
    analyze_keyword_content,
    keyword_in_text,
)
from seo.readability_content import extract_readability_content

ENGINE_VERSION = "1.0"

PLACEMENT_CHECK_IDS = frozenset(
    {
        "keyword_in_seo_title",
        "keyword_in_h1",
        "keyword_in_first_paragraph",
        "keyword_in_url",
        "keyword_in_meta_description",
    }
)

CATEGORY_WEIGHTS: dict[str, int] = {
    "title_optimization": 12,
    "meta_description": 12,
    "keyword_placement": 15,
    "keyword_density": 10,
    "heading_structure": 10,
    "image_alt_text": 8,
    "internal_links": 12,
    "schema_presence": 11,
    "content_length": 10,
}

CATEGORY_LABELS: dict[str, str] = {
    "title_optimization": "Title optimization",
    "meta_description": "Meta description",
    "keyword_placement": "Keyword placement",
    "keyword_density": "Keyword density",
    "heading_structure": "Heading structure",
    "image_alt_text": "Image alt text",
    "internal_links": "Internal links",
    "schema_presence": "Schema.org",
    "content_length": "Content length",
}


def _status_from_score(score: int) -> str:
    if score >= 70:
        return CheckStatus.GOOD.value
    if score >= 40:
        return CheckStatus.OK.value
    return CheckStatus.BAD.value


def _ratio_score(points: int, max_points: int) -> int:
    if max_points <= 0:
        return 0
    return round((points / max_points) * 100)


@dataclass(frozen=True)
class CategoryCheck:
    check_id: str
    label: str
    status: str
    message: str
    score: int
    max_score: int = 100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CategoryScore:
    category_id: str
    label: str
    score: int
    weight: int
    weighted_contribution: float
    status: str
    checks: list[CategoryCheck] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.category_id,
            "label": self.label,
            "score": self.score,
            "weight": self.weight,
            "weighted_contribution": self.weighted_contribution,
            "status": self.status,
            "checks": [check.to_dict() for check in self.checks],
            "recommendations": self.recommendations,
        }


@dataclass
class UnifiedSeoScoreResult:
    overall_score: int = 0
    overall_status: str = CheckStatus.NEUTRAL.value
    categories: list[CategoryScore] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    focus_keyword: str = ""
    word_count: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": ENGINE_VERSION,
            "overall_score": self.overall_score,
            "overall_status": self.overall_status,
            "focus_keyword": self.focus_keyword,
            "word_count": self.word_count,
            "message": self.message,
            "categories": {cat.category_id: cat.to_dict() for cat in self.categories},
            "categories_list": [cat.to_dict() for cat in self.categories],
            "recommendations": self.recommendations,
        }


def _score_title_optimization(analysis_input: ContentAnalysisInput) -> CategoryScore:
    checks: list[CategoryCheck] = []
    recommendations: list[str] = []
    title = analysis_input.seo_title.strip()
    title_len = len(title)

    if 50 <= title_len <= 60:
        length_score = 100
        length_status = CheckStatus.GOOD.value
        length_message = f"SEO title is {title_len} characters — ideal length (50–60)."
    elif 40 <= title_len <= 70:
        length_score = 70
        length_status = CheckStatus.OK.value
        length_message = f"SEO title is {title_len} characters — acceptable (40–70)."
        recommendations.append("Shorten or lengthen the SEO title to 50–60 characters.")
    elif title:
        length_score = 35
        length_status = CheckStatus.BAD.value
        length_message = f"SEO title is {title_len} characters — outside the recommended range."
        recommendations.append("Optimize the SEO title length to 50–60 characters.")
    else:
        length_score = 0
        length_status = CheckStatus.BAD.value
        length_message = "SEO title is empty — the content title is used instead."
        recommendations.append("Enter an SEO title or check the post title.")

    checks.append(
        CategoryCheck(
            check_id="title_length",
            label="SEO title length",
            status=length_status,
            message=length_message,
            score=length_score,
        )
    )

    keyword = analysis_input.focus_keyword.strip()
    if keyword:
        in_title = keyword_in_text(keyword, title)
        kw_score = 100 if in_title else 0
        kw_status = CheckStatus.GOOD.value if in_title else CheckStatus.BAD.value
        kw_message = (
            f'Focus keyword "{keyword}" is in the SEO title.'
            if in_title
            else f'Add the focus keyword "{keyword}" to the SEO title.'
        )
        if not in_title:
            recommendations.append(kw_message)
        checks.append(
            CategoryCheck(
                check_id="keyword_in_title",
                label="Keyword in title",
                status=kw_status,
                message=kw_message,
                score=kw_score,
            )
        )
        score = round((length_score * 0.55) + (kw_score * 0.45))
    else:
        score = length_score
        checks.append(
            CategoryCheck(
                check_id="keyword_in_title",
                label="Keyword in title",
                status=CheckStatus.NEUTRAL.value,
                message="Enter a focus keyword to check the title.",
                score=50,
            )
        )

    return _build_category(
        "title_optimization",
        score=score,
        checks=checks,
        recommendations=recommendations,
    )


def _score_meta_description(analysis_input: ContentAnalysisInput) -> CategoryScore:
    checks: list[CategoryCheck] = []
    recommendations: list[str] = []
    description = analysis_input.meta_description.strip()
    desc_len = len(description)

    if 120 <= desc_len <= 160:
        length_score = 100
        length_status = CheckStatus.GOOD.value
        length_message = f"Meta description is {desc_len} characters — ideal length."
    elif 80 <= desc_len <= 200:
        length_score = 70
        length_status = CheckStatus.OK.value
        length_message = f"Meta description is {desc_len} characters — acceptable."
        recommendations.append("Aim for a meta description of 120–160 characters.")
    elif description:
        length_score = 35
        length_status = CheckStatus.BAD.value
        length_message = f"Meta description is {desc_len} characters — outside the recommended range."
        recommendations.append("Adjust the meta description to 120–160 characters.")
    else:
        length_score = 0
        length_status = CheckStatus.BAD.value
        length_message = "Meta description is empty."
        recommendations.append("Add a meta description (120–160 characters).")

    checks.append(
        CategoryCheck(
            check_id="meta_length",
            label="Meta description length",
            status=length_status,
            message=length_message,
            score=length_score,
        )
    )

    keyword = analysis_input.focus_keyword.strip()
    if keyword:
        in_meta = keyword_in_text(keyword, description)
        kw_score = 100 if in_meta else 0
        kw_status = CheckStatus.GOOD.value if in_meta else CheckStatus.BAD.value
        kw_message = (
            "Focus keyword is in the meta description."
            if in_meta
            else "Include the focus keyword in the meta description."
        )
        if not in_meta:
            recommendations.append(kw_message)
        checks.append(
            CategoryCheck(
                check_id="keyword_in_meta",
                label="Keyword in meta description",
                status=kw_status,
                message=kw_message,
                score=kw_score,
            )
        )
        score = round((length_score * 0.6) + (kw_score * 0.4))
    else:
        score = length_score

    return _build_category(
        "meta_description",
        score=score,
        checks=checks,
        recommendations=recommendations,
    )


def _score_from_keyword_checks(
    keyword_result,
    *,
    category_id: str,
    check_ids: frozenset[str],
) -> CategoryScore:
    selected = [check for check in keyword_result.checks if check.check_id in check_ids]
    if not selected:
        return _build_category(
            category_id,
            score=50,
            checks=[
                CategoryCheck(
                    check_id="not_applicable",
                    label="N/A",
                    status=CheckStatus.NEUTRAL.value,
                    message="Enter a focus keyword for this category.",
                    score=50,
                )
            ],
            recommendations=["Set a focus keyword."],
        )

    checks = [
        CategoryCheck(
            check_id=check.check_id,
            label=check.label,
            status=check.status.value,
            message=check.message,
            score=_ratio_score(check.points, check.max_points),
        )
        for check in selected
    ]
    total_points = sum(check.points for check in selected)
    max_points = sum(check.max_points for check in selected)
    score = _ratio_score(total_points, max_points)
    recommendations = [check.message for check in selected if check.status == CheckStatus.BAD]

    return _build_category(
        category_id,
        score=score,
        checks=checks,
        recommendations=recommendations,
    )


def _score_heading_structure(content_object, *, visible_only: bool) -> CategoryScore:
    checks: list[CategoryCheck] = []
    recommendations: list[str] = []
    readability_input = extract_readability_content(content_object, visible_only=visible_only)
    headings = readability_input.headings

    has_h1 = any(heading.level == "h1" for heading in headings)
    subheadings = [heading for heading in headings if heading.level in {"h2", "h3", "h4"}]

    if has_h1:
        checks.append(
            CategoryCheck(
                check_id="has_h1",
                label="H1 heading",
                status=CheckStatus.GOOD.value,
                message="The page has an H1 heading.",
                score=100,
            )
        )
    else:
        checks.append(
            CategoryCheck(
                check_id="has_h1",
                label="H1 heading",
                status=CheckStatus.BAD.value,
                message="Add one H1 heading in the builder.",
                score=0,
            )
        )
        recommendations.append("Add an H1 heading at the top of the content.")

    if subheadings:
        checks.append(
            CategoryCheck(
                check_id="has_subheadings",
                label="Subheadings (H2–H4)",
                status=CheckStatus.GOOD.value,
                message=f"Found {len(subheadings)} subheadings — good structure.",
                score=100,
            )
        )
    elif readability_input.word_count >= 300:
        checks.append(
            CategoryCheck(
                check_id="has_subheadings",
                label="Subheadings (H2–H4)",
                status=CheckStatus.BAD.value,
                message="Longer text has no subheadings — split content with H2/H3 headings.",
                score=20,
            )
        )
        recommendations.append("Add H2/H3 headings for better structure and SEO.")
    else:
        checks.append(
            CategoryCheck(
                check_id="has_subheadings",
                label="Subheadings (H2–H4)",
                status=CheckStatus.NEUTRAL.value,
                message="Short content — subheadings are optional.",
                score=70,
            )
        )

    score = round(sum(check.score for check in checks) / len(checks))
    return _build_category(
        "heading_structure",
        score=score,
        checks=checks,
        recommendations=recommendations,
    )


def _score_image_alt_text(content_object, metadata) -> CategoryScore:
    from seo.image_seo import analyze_image_seo

    result = analyze_image_seo(content_object, metadata, visible_only=False)
    if result.message and not result.checks:
        return _build_category(
            "image_alt_text",
            score=0,
            checks=[
                CategoryCheck(
                    check_id="image_seo_unavailable",
                    label="Image analysis",
                    status=CheckStatus.NEUTRAL.value,
                    message=result.message,
                    score=0,
                )
            ],
            recommendations=[result.message],
        )

    checks = [
        CategoryCheck(
            check_id=check.check_id,
            label=check.label,
            status=check.status.value,
            message=check.message,
            score=_ratio_score(check.points, check.max_points),
        )
        for check in result.checks
    ]
    return _build_category(
        "image_alt_text",
        score=result.score,
        checks=checks,
        recommendations=result.recommendations,
    )


def _score_internal_links(content_object, metadata) -> CategoryScore:
    if not isinstance(content_object, BlogPost):
        return _build_category(
            "internal_links",
            score=70,
            checks=[
                CategoryCheck(
                    check_id="blog_only",
                    label="Internal links",
                    status=CheckStatus.NEUTRAL.value,
                    message="Detailed internal link analysis is available for blog posts.",
                    score=70,
                )
            ],
            recommendations=[],
        )

    linking_result = analyze_internal_linking(content_object, metadata, visible_only=False)
    checks = [
        CategoryCheck(
            check_id=check.check_id,
            label=check.label,
            status=check.status.value,
            message=check.message,
            score=_ratio_score(check.points, check.max_points),
        )
        for check in linking_result.checks
    ]
    return _build_category(
        "internal_links",
        score=linking_result.score,
        checks=checks,
        recommendations=[
            item
            for item in linking_result.recommendations
            if not item.startswith("Great job")
        ][:5],
    )


def _score_schema_presence(content_object, metadata, request=None) -> CategoryScore:
    from seo.schema.engine import preview_schema_bundle

    if content_object is None or not getattr(content_object, "pk", None):
        return _build_category(
            "schema_presence",
            score=0,
            checks=[
                CategoryCheck(
                    check_id="schema_unavailable",
                    label="Schema.org",
                    status=CheckStatus.NEUTRAL.value,
                    message="Save the content to see Schema.org validation.",
                    score=0,
                )
            ],
            recommendations=["Save the post to generate JSON-LD."],
        )

    try:
        _, _, validation = preview_schema_bundle(
            request,
            content_object,
            metadata=metadata,
            visible_only=False,
        )
    except Exception as exc:  # noqa: BLE001 — keep unified score usable if schema fails
        return _build_category(
            "schema_presence",
            score=0,
            checks=[
                CategoryCheck(
                    check_id="schema_error",
                    label="Schema.org",
                    status=CheckStatus.NEUTRAL.value,
                    message=f"Schema analysis unavailable: {exc}",
                    score=0,
                )
            ],
            recommendations=["Fix schema generation so this category can be scored."],
        )

    checks = [
        CategoryCheck(
            check_id=f"{check.schema_type}:{check.field}",
            label=f"{check.label} ({check.schema_type})",
            status=check.status.value,
            message=check.message,
            score=100 if check.status == CheckStatus.GOOD else 50 if check.status == CheckStatus.OK else 0,
        )
        for check in validation.checks[:8]
    ]
    if not checks:
        checks.append(
            CategoryCheck(
                check_id="schema_generated",
                label="JSON-LD",
                status=CheckStatus.GOOD.value if validation.schema_types else CheckStatus.BAD.value,
                message=(
                    f"Generated types: {', '.join(validation.schema_types)}."
                    if validation.schema_types
                    else "No JSON-LD generated."
                ),
                score=100 if validation.schema_types else 0,
            )
        )

    recommendations = list(validation.warnings[:5]) + [
        check.message
        for check in validation.checks
        if check.status == CheckStatus.BAD
    ][:5]

    return _build_category(
        "schema_presence",
        score=validation.score,
        checks=checks,
        recommendations=recommendations,
    )


def _score_content_length(analysis_input: ContentAnalysisInput, content_object) -> CategoryScore:
    word_count = analysis_input.word_count
    is_blog = isinstance(content_object, BlogPost)
    checks: list[CategoryCheck] = []
    recommendations: list[str] = []

    if is_blog:
        if word_count >= 600:
            score = 100
            status = CheckStatus.GOOD.value
            message = f"Content has {word_count} words — excellent length for a blog post."
        elif word_count >= 300:
            score = 80
            status = CheckStatus.GOOD.value
            message = f"Content has {word_count} words — good length."
        elif word_count >= 150:
            score = 55
            status = CheckStatus.OK.value
            message = f"Content has {word_count} words — consider expanding the text."
            recommendations.append("Expand the article to at least 300 words for better SEO.")
        elif word_count > 0:
            score = 25
            status = CheckStatus.BAD.value
            message = f"Content has only {word_count} words — too short for a blog post."
            recommendations.append("Add more useful content (min. 300 words).")
        else:
            score = 0
            status = CheckStatus.BAD.value
            message = "No text content in the builder."
            recommendations.append("Add content in the builder.")
    else:
        if word_count >= 150:
            score = 100
            status = CheckStatus.GOOD.value
            message = f"The page has {word_count} words."
        elif word_count >= 50:
            score = 70
            status = CheckStatus.OK.value
            message = f"The page has {word_count} words — acceptable for a CMS page."
        elif word_count > 0:
            score = 40
            status = CheckStatus.OK.value
            message = f"The page has {word_count} words."
        else:
            score = 0
            status = CheckStatus.BAD.value
            message = "No text content."
            recommendations.append("Add text content in the builder.")

    checks.append(
        CategoryCheck(
            check_id="word_count",
            label="Word count",
            status=status,
            message=message,
            score=score,
        )
    )

    return _build_category(
        "content_length",
        score=score,
        checks=checks,
        recommendations=recommendations,
    )


def _build_category(
    category_id: str,
    *,
    score: int,
    checks: list[CategoryCheck],
    recommendations: list[str],
) -> CategoryScore:
    weight = CATEGORY_WEIGHTS[category_id]
    weighted = round((score * weight) / 100, 1)
    return CategoryScore(
        category_id=category_id,
        label=CATEGORY_LABELS[category_id],
        score=score,
        weight=weight,
        weighted_contribution=weighted,
        status=_status_from_score(score),
        checks=checks,
        recommendations=recommendations[:5],
    )


def _aggregate_recommendations(categories: list[CategoryScore]) -> list[str]:
    seen: set[str] = set()
    aggregated: list[str] = []

    for category in sorted(categories, key=lambda item: item.score):
        for recommendation in category.recommendations:
            if recommendation and recommendation not in seen:
                seen.add(recommendation)
                aggregated.append(recommendation)

    if not aggregated:
        aggregated.append("Great job — SEO is well optimized.")

    return aggregated[:15]


def analyze_unified_seo(
    content_object,
    metadata=None,
    *,
    request=None,
    overrides: dict | None = None,
    visible_only: bool = False,
) -> UnifiedSeoScoreResult:
    if content_object is None:
        return UnifiedSeoScoreResult(message="No content to analyze.")

    analysis_input = build_content_analysis_input(
        content_object,
        metadata,
        overrides=overrides,
        visible_only=visible_only,
    )
    keyword_result = analyze_keyword_content(analysis_input)

    categories = [
        _score_title_optimization(analysis_input),
        _score_meta_description(analysis_input),
        _score_from_keyword_checks(
            keyword_result,
            category_id="keyword_placement",
            check_ids=PLACEMENT_CHECK_IDS,
        ),
        _score_from_keyword_checks(
            keyword_result,
            category_id="keyword_density",
            check_ids=frozenset({"keyword_density", "keyword_distribution"}),
        ),
        _score_heading_structure(content_object, visible_only=visible_only),
        _score_image_alt_text(content_object, metadata),
        _score_internal_links(content_object, metadata),
        _score_schema_presence(content_object, metadata, request=request),
        _score_content_length(analysis_input, content_object),
    ]

    overall_score = round(sum(category.weighted_contribution for category in categories))
    overall_score = max(0, min(100, overall_score))

    return UnifiedSeoScoreResult(
        overall_score=overall_score,
        overall_status=_status_from_score(overall_score),
        categories=categories,
        recommendations=_aggregate_recommendations(categories),
        focus_keyword=analysis_input.focus_keyword,
        word_count=analysis_input.word_count,
    )


def compute_unified_seo_score(
    content_object,
    metadata=None,
    *,
    request=None,
    visible_only: bool = False,
) -> int:
    """Kratki helper — vraća samo ukupnu ocenu 0–100."""
    result = analyze_unified_seo(
        content_object,
        metadata,
        request=request,
        visible_only=visible_only,
    )
    return result.overall_score

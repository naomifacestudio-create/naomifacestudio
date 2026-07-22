"""AI/LLM readiness analiza — koliko je sadržaj razumljiv AI pretragama i asistentima."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from seo.content_analysis import build_content_analysis_input
from seo.keyword_analyzer import CheckStatus, STATUS_LABELS
from seo.readability_content import build_readability_content_input
from seo.schema.faq import extract_faq_items
from seo.services import get_seo_metadata, resolve_schema_type

FIRST_PARAGRAPH_MIN_WORDS = 25
FIRST_PARAGRAPH_MAX_WORDS = 120
CONTENT_MIN_WORDS = 300
H1_MAX_LENGTH = 90


@dataclass(frozen=True)
class AiReadinessCheck:
    check_id: str
    label: str
    status: CheckStatus
    message: str
    points: int
    max_points: int


@dataclass
class AiReadinessResult:
    score: int = 0
    checks: list[AiReadinessCheck] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "message": self.message,
            "checks": [
                {
                    **asdict(check),
                    "status": check.status.value,
                    "status_label": STATUS_LABELS[check.status],
                }
                for check in self.checks
            ],
            "recommendations": self.recommendations,
        }


def _check_h1(h1: str) -> AiReadinessCheck:
    value = (h1 or "").strip()
    if not value:
        return AiReadinessCheck(
            check_id="ai_h1",
            label="Clear H1 heading",
            status=CheckStatus.BAD,
            message="No H1 heading — AI systems cannot determine the page topic.",
            points=0,
            max_points=20,
        )
    if len(value) > H1_MAX_LENGTH:
        return AiReadinessCheck(
            check_id="ai_h1",
            label="Clear H1 heading",
            status=CheckStatus.OK,
            message=f"H1 is long ({len(value)} characters) — a shorter heading is clearer.",
            points=12,
            max_points=20,
        )
    return AiReadinessCheck(
        check_id="ai_h1",
        label="Clear H1 heading",
        status=CheckStatus.GOOD,
        message="H1 clearly describes the page topic.",
        points=20,
        max_points=20,
    )


def _check_first_paragraph(first_paragraph: str) -> AiReadinessCheck:
    words = len((first_paragraph or "").split())
    if words == 0:
        return AiReadinessCheck(
            check_id="ai_first_paragraph",
            label="Direct answer up front",
            status=CheckStatus.BAD,
            message="No intro paragraph — start with a direct answer to the main question.",
            points=0,
            max_points=20,
        )
    if words < FIRST_PARAGRAPH_MIN_WORDS:
        return AiReadinessCheck(
            check_id="ai_first_paragraph",
            label="Direct answer up front",
            status=CheckStatus.OK,
            message=f"Intro paragraph is short ({words} words) — expand it into a standalone answer.",
            points=10,
            max_points=20,
        )
    if words > FIRST_PARAGRAPH_MAX_WORDS:
        return AiReadinessCheck(
            check_id="ai_first_paragraph",
            label="Direct answer up front",
            status=CheckStatus.OK,
            message=f"Intro paragraph is long ({words} words) — summarize the key answer.",
            points=12,
            max_points=20,
        )
    return AiReadinessCheck(
        check_id="ai_first_paragraph",
        label="Direct answer up front",
        status=CheckStatus.GOOD,
        message=f"Intro paragraph ({words} words) gives a standalone answer.",
        points=20,
        max_points=20,
    )


def _check_headings_structure(headings) -> AiReadinessCheck:
    subheadings = [entry for entry in headings if entry.level != "h1"]
    if len(subheadings) >= 2:
        return AiReadinessCheck(
            check_id="ai_headings",
            label="Subheading structure",
            status=CheckStatus.GOOD,
            message=f"{len(subheadings)} subheadings — content is easy to parse by section.",
            points=15,
            max_points=15,
        )
    if len(subheadings) == 1:
        return AiReadinessCheck(
            check_id="ai_headings",
            label="Subheading structure",
            status=CheckStatus.OK,
            message="Only one subheading — split content into more clear sections.",
            points=8,
            max_points=15,
        )
    return AiReadinessCheck(
        check_id="ai_headings",
        label="Subheading structure",
        status=CheckStatus.BAD,
        message="No subheadings (H2/H3) — AI struggles to extract answers from unbroken text.",
        points=0,
        max_points=15,
    )


def _check_faq(content_object) -> AiReadinessCheck:
    faq_items = extract_faq_items(content_object, visible_only=False)
    if len(faq_items) >= 2:
        return AiReadinessCheck(
            check_id="ai_faq",
            label="FAQ content",
            status=CheckStatus.GOOD,
            message=f"{len(faq_items)} FAQ pairs — ideal for AI answers and rich results.",
            points=15,
            max_points=15,
        )
    if len(faq_items) == 1:
        return AiReadinessCheck(
            check_id="ai_faq",
            label="FAQ content",
            status=CheckStatus.OK,
            message="One FAQ pair — add more questions users actually ask.",
            points=8,
            max_points=15,
        )
    return AiReadinessCheck(
        check_id="ai_faq",
        label="FAQ content",
        status=CheckStatus.OK,
        message="No FAQ block — Q&A helps AI systems cite the content.",
        points=5,
        max_points=15,
    )


def _check_schema(content_object, metadata) -> AiReadinessCheck:
    schema_type = resolve_schema_type(content_object, metadata)
    if schema_type:
        return AiReadinessCheck(
            check_id="ai_schema",
            label="Structured data",
            status=CheckStatus.GOOD,
            message=f"JSON-LD schema is active ({schema_type}).",
            points=15,
            max_points=15,
        )
    return AiReadinessCheck(
        check_id="ai_schema",
        label="Structured data",
        status=CheckStatus.BAD,
        message="No JSON-LD schema — structured data is a key signal for AI search.",
        points=0,
        max_points=15,
    )


def _check_content_depth(word_count: int) -> AiReadinessCheck:
    if word_count >= CONTENT_MIN_WORDS:
        return AiReadinessCheck(
            check_id="ai_content_depth",
            label="Content depth",
            status=CheckStatus.GOOD,
            message=f"Content of {word_count} words provides enough context.",
            points=15,
            max_points=15,
        )
    if word_count >= CONTENT_MIN_WORDS // 2:
        return AiReadinessCheck(
            check_id="ai_content_depth",
            label="Content depth",
            status=CheckStatus.OK,
            message=f"Content of {word_count} words is thin — aim for {CONTENT_MIN_WORDS}+ words.",
            points=8,
            max_points=15,
        )
    return AiReadinessCheck(
        check_id="ai_content_depth",
        label="Content depth",
        status=CheckStatus.BAD,
        message=f"Only {word_count} words — too short for reliable AI answers.",
        points=0,
        max_points=15,
    )


def analyze_ai_readiness(
    content_object,
    metadata=None,
    *,
    overrides: dict | None = None,
    visible_only: bool = False,
) -> AiReadinessResult:
    if content_object is None or not getattr(content_object, "pk", None):
        return AiReadinessResult(
            message="Save the post to see the AI readiness analysis.",
        )

    metadata = metadata if metadata is not None else get_seo_metadata(content_object)
    analysis_input = build_content_analysis_input(
        content_object,
        metadata,
        overrides=overrides,
        visible_only=visible_only,
    )
    readability_input = build_readability_content_input(
        content_object,
        overrides=overrides,
        visible_only=visible_only,
    )

    checks = [
        _check_h1(analysis_input.h1),
        _check_first_paragraph(analysis_input.first_paragraph),
        _check_headings_structure(readability_input.headings),
        _check_faq(content_object),
        _check_schema(content_object, metadata),
        _check_content_depth(analysis_input.word_count),
    ]

    total_points = sum(check.points for check in checks)
    max_points = sum(check.max_points for check in checks)
    score = round((total_points / max_points) * 100) if max_points else 0

    recommendations: list[str] = []
    for check in checks:
        if check.points < check.max_points:
            recommendations.append(check.message)
    if not recommendations:
        recommendations.append("Great — content is ready for AI search and assistants.")

    return AiReadinessResult(
        score=score,
        checks=checks,
        recommendations=recommendations[:8],
    )

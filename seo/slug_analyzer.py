"""Analiza URL slug-a — dužina, format, jedinstvenost i ključna reč."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from django.contrib.contenttypes.models import ContentType

from seo.keyword_analyzer import CheckStatus, STATUS_LABELS, keyword_in_slug

SLUG_IDEAL_MAX_LENGTH = 75
SLUG_WARN_MAX_LENGTH = 90

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

SLUG_STOP_WORDS = frozenset(
    {
        "a",
        "i",
        "u",
        "na",
        "za",
        "od",
        "do",
        "sa",
        "s",
        "o",
        "the",
        "and",
        "or",
        "to",
        "of",
        "in",
        "is",
        "kako",
        "sta",
        "šta",
        "koji",
        "koja",
        "koje",
    }
)


@dataclass(frozen=True)
class SlugCheck:
    check_id: str
    label: str
    status: CheckStatus
    message: str
    points: int
    max_points: int


@dataclass
class SlugAnalysisResult:
    slug: str
    score: int = 0
    checks: list[SlugCheck] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    preview_url: str = ""
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "score": self.score,
            "preview_url": self.preview_url,
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


def _check_length(slug: str) -> SlugCheck:
    length = len(slug)
    if not slug:
        return SlugCheck(
            check_id="slug_length",
            label="Slug length",
            status=CheckStatus.BAD,
            message="Slug is empty.",
            points=0,
            max_points=20,
        )
    if length <= SLUG_IDEAL_MAX_LENGTH:
        return SlugCheck(
            check_id="slug_length",
            label="Slug length",
            status=CheckStatus.GOOD,
            message=f"Length is fine ({length} characters).",
            points=20,
            max_points=20,
        )
    if length <= SLUG_WARN_MAX_LENGTH:
        return SlugCheck(
            check_id="slug_length",
            label="Slug length",
            status=CheckStatus.OK,
            message=f"Slug is long ({length} characters) — shorten it if possible.",
            points=12,
            max_points=20,
        )
    return SlugCheck(
        check_id="slug_length",
        label="Slug length",
        status=CheckStatus.BAD,
        message=f"Slug is too long ({length} characters).",
        points=0,
        max_points=20,
    )


def _check_charset(slug: str) -> SlugCheck:
    if not slug:
        return SlugCheck(
            check_id="slug_charset",
            label="Allowed characters",
            status=CheckStatus.BAD,
            message="Slug is empty.",
            points=0,
            max_points=20,
        )
    if slug != slug.lower():
        return SlugCheck(
            check_id="slug_charset",
            label="Allowed characters",
            status=CheckStatus.BAD,
            message="Use only lowercase letters, numbers, and hyphens.",
            points=0,
            max_points=20,
        )
    if not SLUG_PATTERN.match(slug):
        return SlugCheck(
            check_id="slug_charset",
            label="Allowed characters",
            status=CheckStatus.BAD,
            message="Slug may contain only lowercase letters, numbers, and single hyphens.",
            points=0,
            max_points=20,
        )
    return SlugCheck(
        check_id="slug_charset",
        label="Allowed characters",
        status=CheckStatus.GOOD,
        message="Slug format is valid.",
        points=20,
        max_points=20,
    )


def _check_stop_words(slug: str) -> SlugCheck:
    if not slug:
        return SlugCheck(
            check_id="slug_stop_words",
            label="Stop words",
            status=CheckStatus.NEUTRAL,
            message="No slug to check.",
            points=10,
            max_points=15,
        )
    parts = [part for part in slug.split("-") if part]
    if not parts:
        return SlugCheck(
            check_id="slug_stop_words",
            label="Stop words",
            status=CheckStatus.BAD,
            message="Slug has no meaningful words.",
            points=0,
            max_points=15,
        )
    if parts[0] in SLUG_STOP_WORDS or parts[-1] in SLUG_STOP_WORDS:
        return SlugCheck(
            check_id="slug_stop_words",
            label="Stop words",
            status=CheckStatus.OK,
            message="Slug starts or ends with a stop word — remove it if possible.",
            points=8,
            max_points=15,
        )
    return SlugCheck(
        check_id="slug_stop_words",
        label="Stop words",
        status=CheckStatus.GOOD,
        message="Slug does not start or end with a stop word.",
        points=15,
        max_points=15,
    )


def _check_keyword(slug: str, focus_keyword: str) -> SlugCheck:
    if not focus_keyword.strip():
        return SlugCheck(
            check_id="slug_keyword",
            label="Keyword in slug",
            status=CheckStatus.NEUTRAL,
            message="Enter a focus keyword to check the slug.",
            points=10,
            max_points=15,
        )
    if keyword_in_slug(focus_keyword, slug):
        return SlugCheck(
            check_id="slug_keyword",
            label="Keyword in slug",
            status=CheckStatus.GOOD,
            message=f'Slug "{slug}" contains the focus keyword.',
            points=15,
            max_points=15,
        )
    return SlugCheck(
        check_id="slug_keyword",
        label="Keyword in slug",
        status=CheckStatus.BAD,
        message="Adjust the slug to include the main focus keyword.",
        points=0,
        max_points=15,
    )


def _slug_is_duplicate(
    slug: str,
    *,
    content_type_id: int | None,
    object_id: int | None,
) -> bool:
    if not slug:
        return False

    from blogs.models import BlogPost
    from core.models import CMSPage
    from education.models import Education
    from treatments.models import Treatment

    def _slug_taken(model, field_names):
        qs = model.objects.none()
        for field_name in field_names:
            qs = qs | model.objects.filter(**{field_name: slug})
        if content_type_id and object_id:
            model_ct = ContentType.objects.get_for_model(model)
            if content_type_id == model_ct.id:
                qs = qs.exclude(pk=object_id)
        return qs.exists()

    if _slug_taken(BlogPost, ("slug_hr", "slug_en")):
        return True
    if _slug_taken(Education, ("slug_hr", "slug_en")):
        return True
    if _slug_taken(Treatment, ("slug_hr", "slug_en")):
        return True

    # CMSPage is a non-model stub — skip uniqueness against CMS.
    if not hasattr(CMSPage, "_meta"):
        return False

    cms_qs = CMSPage.objects.filter(slug=slug)
    if content_type_id and object_id:
        try:
            cms_ct = ContentType.objects.get_for_model(CMSPage)
        except Exception:
            return False
        if content_type_id == cms_ct.id:
            cms_qs = cms_qs.exclude(pk=object_id)
    return bool(getattr(cms_qs, "exists", lambda: False)())


def _check_uniqueness(
    slug: str,
    *,
    content_type_id: int | None,
    object_id: int | None,
) -> SlugCheck:
    if not slug:
        return SlugCheck(
            check_id="slug_unique",
            label="Uniqueness",
            status=CheckStatus.NEUTRAL,
            message="No slug to check.",
            points=15,
            max_points=15,
        )
    if _slug_is_duplicate(slug, content_type_id=content_type_id, object_id=object_id):
        return SlugCheck(
            check_id="slug_unique",
            label="Uniqueness",
            status=CheckStatus.BAD,
            message="This slug already exists — choose another.",
            points=0,
            max_points=15,
        )
    return SlugCheck(
        check_id="slug_unique",
        label="Uniqueness",
        status=CheckStatus.GOOD,
        message="Slug is unique.",
        points=15,
        max_points=15,
    )


def _build_preview_url(slug: str) -> str:
    slug = slug.strip().strip("/")
    if not slug:
        return "/blog/"
    return f"/blog/{slug}/"


def analyze_slug(
    slug: str,
    *,
    focus_keyword: str = "",
    content_type_id: int | None = None,
    object_id: int | None = None,
) -> SlugAnalysisResult:
    normalized = (slug or "").strip().strip("/")
    checks = [
        _check_length(normalized),
        _check_charset(normalized),
        _check_stop_words(normalized),
        _check_keyword(normalized, focus_keyword),
        _check_uniqueness(
            normalized,
            content_type_id=content_type_id,
            object_id=object_id,
        ),
    ]

    total_points = sum(check.points for check in checks)
    max_points = sum(check.max_points for check in checks)
    score = round((total_points / max_points) * 100) if max_points else 0

    recommendations: list[str] = []
    for check in checks:
        if check.status in {CheckStatus.BAD, CheckStatus.OK} and check.points < check.max_points:
            recommendations.append(check.message)
    if not recommendations:
        recommendations.append("Slug is well optimized.")

    return SlugAnalysisResult(
        slug=normalized,
        score=score,
        checks=checks,
        recommendations=recommendations[:8],
        preview_url=_build_preview_url(normalized),
    )


def analyze_slug_for_object(
    content_object,
    metadata=None,
    *,
    overrides: dict | None = None,
) -> SlugAnalysisResult:
    overrides = overrides or {}
    slug = overrides.get("url_slug")
    if slug is None:
        slug = getattr(content_object, "slug", "") if content_object else ""
    focus_keyword = overrides.get("focus_keyword")
    if focus_keyword is None and metadata is not None:
        focus_keyword = metadata.focus_keyword
    focus_keyword = (focus_keyword or "").strip()

    content_type_id = None
    object_id = None
    if content_object is not None and getattr(content_object, "pk", None):
        content_type_id = ContentType.objects.get_for_model(content_object).id
        object_id = content_object.pk

    return analyze_slug(
        str(slug or ""),
        focus_keyword=focus_keyword,
        content_type_id=content_type_id,
        object_id=object_id,
    )

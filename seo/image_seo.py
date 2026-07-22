"""Image SEO analiza — alt tekst, nazivi fajlova, dimenzije i kompresija."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field

from seo.image_seo_content import (
    PageImageEntry,
    collect_page_images,
    collect_page_images_from_body_page,
)
from seo.keyword_analyzer import CheckStatus

IMAGE_MIN_DIMENSION = 200
IMAGE_RECOMMENDED_MAX_WIDTH = 1920
IMAGE_RECOMMENDED_MAX_HEIGHT = 1920
IMAGE_COMPRESS_WARN_BYTES = 300 * 1024
IMAGE_COMPRESS_BAD_BYTES = 800 * 1024

GENERIC_FILENAME_PATTERNS = (
    re.compile(r"^img[_\-]?\d+", re.I),
    re.compile(r"^dsc[_\-]?\d+", re.I),
    re.compile(r"^image\d*$", re.I),
    re.compile(r"^photo\d*$", re.I),
    re.compile(r"^screenshot", re.I),
    re.compile(r"^snap[_\-]?", re.I),
    re.compile(r"^[a-f0-9]{16,}$", re.I),
    re.compile(r"^\d+$"),
)

STATUS_LABELS = {
    CheckStatus.GOOD: "Great",
    CheckStatus.OK: "OK",
    CheckStatus.BAD: "Needs improvement",
    CheckStatus.NEUTRAL: "N/A",
}


@dataclass(frozen=True)
class ImageSeoCheck:
    check_id: str
    label: str
    status: CheckStatus
    message: str
    points: int
    max_points: int


@dataclass(frozen=True)
class ImageIssue:
    filename: str
    label: str
    issue: str
    severity: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ImageSeoResult:
    score: int = 0
    image_count: int = 0
    checks: list[ImageSeoCheck] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    issues: list[ImageIssue] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "image_count": self.image_count,
            "checks": [
                {
                    **asdict(check),
                    "status": check.status.value,
                    "status_label": STATUS_LABELS[check.status],
                }
                for check in self.checks
            ],
            "recommendations": self.recommendations,
            "issues": [issue.to_dict() for issue in self.issues],
            "images": self.images,
            "message": self.message,
        }


def _ratio_score(good: int, total: int, *, max_points: int) -> tuple[int, CheckStatus]:
    if total <= 0:
        return max_points, CheckStatus.NEUTRAL
    ratio = good / total
    if ratio >= 0.95:
        return max_points, CheckStatus.GOOD
    if ratio >= 0.7:
        return max(max_points // 2, 1), CheckStatus.OK
    if ratio >= 0.4:
        return max(max_points // 4, 1), CheckStatus.OK
    return 0, CheckStatus.BAD


def _is_descriptive_filename(stem: str) -> bool:
    if len(stem) < 4:
        return False
    for pattern in GENERIC_FILENAME_PATTERNS:
        if pattern.search(stem):
            return False
    if not re.search(r"[a-z]", stem, re.I):
        return False
    parts = [part for part in re.split(r"[-_]+", stem) if part]
    if len(parts) >= 2:
        return True
    return len(stem) >= 10 and not re.search(r"\d{5,}", stem)


def _analyze_filename(entry: PageImageEntry) -> tuple[bool, str]:
    stem = entry.stem
    if _is_descriptive_filename(stem):
        return True, "Descriptive filename"
    if len(stem) < 4:
        return False, "Prekratak naziv fajla"
    for pattern in GENERIC_FILENAME_PATTERNS:
        if pattern.search(stem):
            return False, "Generic name (IMG_, DSC_, …)"
    if re.search(r"\d{5,}", stem):
        return False, "Name contains long numeric sequences"
    return False, "Use a descriptive hyphenated name, e.g. corrective-exercises-hip.jpg"


def _analyze_dimensions(entry: PageImageEntry) -> tuple[bool, str]:
    width = entry.width or 0
    height = entry.height or 0
    if not width or not height:
        return False, "Dimensions unavailable"
    if width < IMAGE_MIN_DIMENSION or height < IMAGE_MIN_DIMENSION:
        return False, f"Image too small ({width}×{height}px)"
    if width > IMAGE_RECOMMENDED_MAX_WIDTH or height > IMAGE_RECOMMENDED_MAX_HEIGHT:
        return False, f"Prevelika za web ({width}×{height}px) — smanjite ili kompresujte"
    return True, f"Dimensions look good ({width}×{height}px)"


def _analyze_compression(entry: PageImageEntry) -> tuple[bool, str]:
    size = entry.file_size
    if size <= 0:
        return True, "File size not checked"
    if size >= IMAGE_COMPRESS_BAD_BYTES:
        kb = round(size / 1024)
        return False, f"Veliki fajl ({kb} KB) — kompresujte ili konvertujte u WebP"
    if size >= IMAGE_COMPRESS_WARN_BYTES:
        kb = round(size / 1024)
        hint = "WebP"
        if entry.format_name == "PNG":
            hint = "PNG → WebP/JPEG"
        return False, f"Fajl od {kb} KB — razmislite o {hint} kompresiji"
    return True, "File size is acceptable"


def _analyze_lazy_loading(images: list[PageImageEntry]) -> tuple[int, CheckStatus, str, list[ImageIssue]]:
    if not images:
        return 15, CheckStatus.NEUTRAL, "No images to check lazy-loading strategy.", []

    issues: list[ImageIssue] = []
    eager_images = [entry for entry in images if entry.loading == "eager"]
    lazy_images = [entry for entry in images if entry.loading == "lazy"]

    if not eager_images:
        issues.append(
            ImageIssue(
                filename="—",
                label="LCP / first image",
                issue='No eager image — the first visible image should use loading="eager".',
                severity=CheckStatus.BAD.value,
            )
        )
        return 0, CheckStatus.BAD, "No eager image for faster LCP.", issues

    if len(eager_images) > 2:
        for entry in eager_images[2:]:
            issues.append(
                ImageIssue(
                    filename=entry.basename,
                    label=entry.label,
                    issue="Too many eager images — use lazy for images below the fold.",
                    severity=CheckStatus.OK.value,
                )
            )
        return 8, CheckStatus.OK, f"{len(eager_images)} eager images — keep eager only for the LCP image.", issues

    below_fold_eager = [
        entry
        for entry in eager_images[1:]
        if entry.source == "page_image"
    ]
    for entry in below_fold_eager:
        issues.append(
            ImageIssue(
                filename=entry.basename,
                label=entry.label,
                issue='Below-the-fold images should use loading="lazy".',
                severity=CheckStatus.OK.value,
            )
        )

    if below_fold_eager:
        return 10, CheckStatus.OK, "First image is eager, but some later ones are too — switch them to lazy.", issues

    if not lazy_images and len(images) > 1:
        return 10, CheckStatus.OK, "All images are eager — consider lazy for the rest.", issues

    return 15, CheckStatus.GOOD, "Lazy-loading strategy looks good (eager for LCP, lazy for the rest).", issues


def analyze_image_seo(
    content_object,
    metadata=None,
    *,
    visible_only: bool = False,
    body_page: dict | None = None,
) -> ImageSeoResult:
    if content_object is None or not getattr(content_object, "pk", None):
        return ImageSeoResult(
            message="Save the post to run the image analysis.",
        )

    if isinstance(body_page, dict):
        images = collect_page_images_from_body_page(
            content_object,
            body_page,
            visible_only=visible_only,
        )
    else:
        images = collect_page_images(content_object, visible_only=visible_only)
    if not images:
        return ImageSeoResult(
            score=70,
            image_count=0,
            checks=[
                ImageSeoCheck(
                    check_id="images_present",
                    label="Images in content",
                    status=CheckStatus.NEUTRAL,
                    message="No images — add images in the builder or a featured image.",
                    points=14,
                    max_points=20,
                )
            ],
            recommendations=["Add images with descriptive alt text and optimized filenames."],
        )

    issues: list[ImageIssue] = []
    image_rows: list[dict] = []

    missing_alt = [entry for entry in images if not entry.has_alt]
    alt_good = len(images) - len(missing_alt)
    alt_points, alt_status = _ratio_score(alt_good, len(images), max_points=25)
    for entry in missing_alt:
        issues.append(
            ImageIssue(
                filename=entry.basename,
                label=entry.label,
                issue="Missing alt text",
                severity=CheckStatus.BAD.value,
            )
        )

    alt_values = [entry.alt_text.strip().lower() for entry in images if entry.has_alt]
    duplicate_alts = [alt for alt, count in Counter(alt_values).items() if count > 1]
    if duplicate_alts:
        dup_status = CheckStatus.BAD if len(duplicate_alts) > 1 else CheckStatus.OK
        dup_points = 0 if dup_status == CheckStatus.BAD else 10
        dup_message = (
            f"{len(duplicate_alts)} duplicate alt text(s) — each image needs a unique description."
        )
        for entry in images:
            if entry.alt_text.strip().lower() in duplicate_alts:
                issues.append(
                    ImageIssue(
                        filename=entry.basename,
                        label=entry.label,
                        issue=f'Duplicate alt: "{entry.alt_text.strip()}"',
                        severity=CheckStatus.BAD.value,
                    )
                )
    else:
        dup_status = CheckStatus.GOOD
        dup_points = 15
        dup_message = "No duplicate alt texts."

    filename_good = 0
    for entry in images:
        ok, detail = _analyze_filename(entry)
        if ok:
            filename_good += 1
        else:
            issues.append(
                ImageIssue(
                    filename=entry.basename,
                    label=entry.label,
                    issue=detail,
                    severity=CheckStatus.OK.value,
                )
            )
    fn_points, fn_status = _ratio_score(filename_good, len(images), max_points=20)

    dimension_good = 0
    for entry in images:
        ok, detail = _analyze_dimensions(entry)
        if ok:
            dimension_good += 1
        else:
            issues.append(
                ImageIssue(
                    filename=entry.basename,
                    label=entry.label,
                    issue=detail,
                    severity=CheckStatus.BAD.value if "too small" in detail.lower() else CheckStatus.OK.value,
                )
            )
    dim_points, dim_status = _ratio_score(dimension_good, len(images), max_points=20)

    compression_good = 0
    for entry in images:
        ok, detail = _analyze_compression(entry)
        if ok:
            compression_good += 1
        else:
            issues.append(
                ImageIssue(
                    filename=entry.basename,
                    label=entry.label,
                    issue=detail,
                    severity=CheckStatus.BAD.value if entry.file_size >= IMAGE_COMPRESS_BAD_BYTES else CheckStatus.OK.value,
                )
            )
    comp_points, comp_status = _ratio_score(compression_good, len(images), max_points=15)

    lazy_points, lazy_status, lazy_message, lazy_issues = _analyze_lazy_loading(images)
    issues.extend(lazy_issues)

    checks = [
        ImageSeoCheck(
            check_id="alt_text_coverage",
            label="Alt text",
            status=alt_status,
            message=(
                f"{alt_good}/{len(images)} images have alt text."
                if alt_good
                else "No images have alt text."
            ),
            points=alt_points,
            max_points=25,
        ),
        ImageSeoCheck(
            check_id="duplicate_alt_text",
            label="Duplicate alt text",
            status=dup_status,
            message=dup_message,
            points=dup_points,
            max_points=15,
        ),
        ImageSeoCheck(
            check_id="filename_quality",
            label="Filename quality",
            status=fn_status,
            message=f"{filename_good}/{len(images)} images have descriptive filenames.",
            points=fn_points,
            max_points=20,
        ),
        ImageSeoCheck(
            check_id="image_dimensions",
            label="Image dimensions",
            status=dim_status,
            message=f"{dimension_good}/{len(images)} images have appropriate dimensions.",
            points=dim_points,
            max_points=20,
        ),
        ImageSeoCheck(
            check_id="compression",
            label="Compression",
            status=comp_status,
            message=f"{compression_good}/{len(images)} images are sufficiently compressed.",
            points=comp_points,
            max_points=15,
        ),
        ImageSeoCheck(
            check_id="lazy_loading",
            label="Lazy-loading",
            status=lazy_status,
            message=lazy_message,
            points=lazy_points,
            max_points=15,
        ),
    ]

    for entry in images:
        image_rows.append(
            {
                "label": entry.label,
                "source": entry.source,
                "filename": entry.basename,
                "alt_text": entry.alt_text or "—",
                "width": entry.width,
                "height": entry.height,
                "file_size_kb": round(entry.file_size / 1024) if entry.file_size else None,
                "format": entry.format_name or "—",
                "loading": entry.loading or "—",
            }
        )

    total_points = sum(check.points for check in checks)
    max_total = sum(check.max_points for check in checks)
    score = round((total_points / max_total) * 100) if max_total else 0

    recommendations: list[str] = []
    for check in checks:
        if check.status == CheckStatus.BAD:
            recommendations.append(check.message)
    for issue in issues[:8]:
        recommendations.append(f"{issue.label}: {issue.issue}")
    if not recommendations:
        recommendations.append("Great job — images are well optimized for SEO.")

    return ImageSeoResult(
        score=score,
        image_count=len(images),
        checks=checks,
        recommendations=recommendations[:12],
        issues=issues,
        images=image_rows,
    )

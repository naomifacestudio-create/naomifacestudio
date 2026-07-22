"""Google SERP preview — naslov, URL, meta opis i upozorenja o dužini."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from urllib.parse import urlparse

from django.conf import settings

from seo.canonical import build_absolute_canonical, get_site_base_url, normalize_path
from seo.constants import (
    META_DESCRIPTION_MAX_LENGTH,
    SEO_TITLE_MAX_LENGTH,
    SERP_DESCRIPTION_DESKTOP_DISPLAY_MAX,
    SERP_DESCRIPTION_IDEAL_MAX,
    SERP_DESCRIPTION_IDEAL_MIN,
    SERP_DESCRIPTION_MOBILE_DISPLAY_MAX,
    SERP_TITLE_DESKTOP_DISPLAY_MAX,
    SERP_TITLE_IDEAL_MAX,
    SERP_TITLE_IDEAL_MIN,
    SERP_TITLE_MOBILE_DISPLAY_MAX,
)
from seo.services import (
    get_seo_fallback_title,
    resolve_canonical_url,
    resolve_meta_description,
    resolve_seo_title,
)


class LimitStatus(StrEnum):
    GOOD = "good"
    OK = "ok"
    BAD = "bad"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class SerpLimitWarning:
    field: str
    label: str
    status: LimitStatus
    message: str
    length: int
    ideal_min: int | None = None
    ideal_max: int | None = None
    display_max_desktop: int | None = None
    display_max_mobile: int | None = None

    def to_dict(self) -> dict:
        return {
            **asdict(self),
            "status": self.status.value,
        }


@dataclass
class SerpPreview:
    title: str
    url: str
    display_url: str
    description: str
    title_desktop: str
    title_mobile: str
    description_desktop: str
    description_mobile: str
    warnings: list[SerpLimitWarning] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "display_url": self.display_url,
            "description": self.description,
            "title_desktop": self.title_desktop,
            "title_mobile": self.title_mobile,
            "description_desktop": self.description_desktop,
            "description_mobile": self.description_mobile,
            "warnings": [warning.to_dict() for warning in self.warnings],
            "sources": self.sources,
        }


def _truncate(text: str, max_length: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_length:
        return cleaned
    if max_length <= 1:
        return "…"
    return f"{cleaned[: max_length - 1].rstrip()}…"


def _format_display_url(url: str) -> str:
    if not url:
        site = get_site_base_url()
        if site:
            parsed = urlparse(site)
            return parsed.netloc or site.replace("https://", "").replace("http://", "")
        return getattr(settings, "SITE_NAME", "example.com")

    parsed = urlparse(url)
    domain = parsed.netloc or url.replace("https://", "").replace("http://", "").split("/")[0]
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return domain
    return " › ".join([domain, *parts[:4]])


def _resolve_draft_url(
    *,
    request,
    content_object,
    canonical_override: str,
    url_slug: str,
) -> tuple[str, str]:
    if canonical_override.strip():
        url = canonical_override.strip()
        return url, "manual"

    if content_object is not None and hasattr(content_object, "get_absolute_url"):
        path = content_object.get_absolute_url()
        if request:
            url = build_absolute_canonical(path, request)
        else:
            base = get_site_base_url()
            url = f"{base}{normalize_path(path)}" if base else normalize_path(path)
        return url, "automatic"

    slug = (url_slug or "").strip().strip("/")
    if slug:
        path = normalize_path(f"/blog/{slug}/")
    else:
        path = "/"

    base = get_site_base_url()
    if base:
        return f"{base}{path}", "draft"
    if request:
        return build_absolute_canonical(path, request), "draft"
    return path, "draft"


def _length_warning(
    *,
    field: str,
    label: str,
    text: str,
    ideal_min: int,
    ideal_max: int,
    hard_max: int,
    display_max_desktop: int,
    display_max_mobile: int,
    empty_message: str,
) -> SerpLimitWarning:
    length = len(text.strip())

    if not text.strip():
        return SerpLimitWarning(
            field=field,
            label=label,
            status=LimitStatus.BAD,
            message=empty_message,
            length=0,
            ideal_min=ideal_min,
            ideal_max=ideal_max,
            display_max_desktop=display_max_desktop,
            display_max_mobile=display_max_mobile,
        )

    if ideal_min <= length <= ideal_max:
        status = LimitStatus.GOOD
        message = f"{label} is {length} characters — ideal length ({ideal_min}–{ideal_max})."
    elif length < ideal_min:
        status = LimitStatus.OK if length >= ideal_min - 15 else LimitStatus.BAD
        message = (
            f"{label} is {length} characters — too short. "
            f"Aim for {ideal_min}–{ideal_max} characters."
        )
    elif length <= hard_max:
        status = LimitStatus.OK
        message = (
            f"{label} is {length} characters — acceptable, but ideal is "
            f"{ideal_min}–{ideal_max}."
        )
    else:
        status = LimitStatus.BAD
        message = (
            f"{label} is {length} characters — exceeds the field maximum ({hard_max})."
        )

    if length > display_max_desktop and status != LimitStatus.BAD:
        message += f" Google may truncate the display after ~{display_max_desktop} characters on desktop."

    return SerpLimitWarning(
        field=field,
        label=label,
        status=status,
        message=message,
        length=length,
        ideal_min=ideal_min,
        ideal_max=ideal_max,
        display_max_desktop=display_max_desktop,
        display_max_mobile=display_max_mobile,
    )


def build_serp_preview(
    content_object,
    request=None,
    metadata=None,
    *,
    overrides: dict | None = None,
) -> SerpPreview:
    overrides = overrides or {}

    title_override = overrides.get("seo_title")
    if title_override is None and metadata is not None:
        title = resolve_seo_title(content_object, metadata)
        title_source = "manual" if metadata.seo_title.strip() else "fallback"
    else:
        title = (title_override or "").strip()
        if not title and content_object is not None:
            title = get_seo_fallback_title(content_object)
            title_source = "fallback"
        else:
            title_source = "manual" if title_override else "fallback"

    article_title = overrides.get("article_title", "")
    if not title and article_title:
        title = article_title.strip()
        title_source = "fallback"

    description_override = overrides.get("meta_description")
    if description_override is None and metadata is not None:
        description = resolve_meta_description(content_object, metadata)
        description_source = "manual" if metadata.meta_description.strip() else "fallback"
    else:
        description = (description_override or "").strip()
        if not description and content_object is not None:
            description = resolve_meta_description(content_object, metadata)
            description_source = "fallback"
        else:
            description_source = "manual" if description_override else "fallback"

    excerpt = overrides.get("excerpt", "").strip()
    if not description and excerpt:
        description = excerpt
        description_source = "fallback"

    canonical_override = (overrides.get("canonical_url") or "").strip()
    if not canonical_override and metadata is not None:
        canonical_override = metadata.canonical_url.strip()

    url_slug = overrides.get(
        "url_slug",
        getattr(content_object, "slug", "") if content_object else "",
    )
    url, url_source = _resolve_draft_url(
        request=request,
        content_object=content_object,
        canonical_override=canonical_override,
        url_slug=url_slug,
    )

    if content_object is not None and not canonical_override:
        resolved = resolve_canonical_url(content_object, request, metadata)
        if resolved:
            url = resolved
            url_source = "automatic"
    elif canonical_override:
        url_source = "manual"

    warnings = [
        _length_warning(
            field="title",
            label="SEO title",
            text=title,
            ideal_min=SERP_TITLE_IDEAL_MIN,
            ideal_max=SERP_TITLE_IDEAL_MAX,
            hard_max=SEO_TITLE_MAX_LENGTH,
            display_max_desktop=SERP_TITLE_DESKTOP_DISPLAY_MAX,
            display_max_mobile=SERP_TITLE_MOBILE_DISPLAY_MAX,
            empty_message="SEO title is empty — Google will use the page title.",
        ),
        _length_warning(
            field="description",
            label="Meta description",
            text=description,
            ideal_min=SERP_DESCRIPTION_IDEAL_MIN,
            ideal_max=SERP_DESCRIPTION_IDEAL_MAX,
            hard_max=META_DESCRIPTION_MAX_LENGTH,
            display_max_desktop=SERP_DESCRIPTION_DESKTOP_DISPLAY_MAX,
            display_max_mobile=SERP_DESCRIPTION_MOBILE_DISPLAY_MAX,
            empty_message="Meta description is empty — Google may generate the snippet itself.",
        ),
    ]

    return SerpPreview(
        title=title,
        url=url,
        display_url=_format_display_url(url),
        description=description,
        title_desktop=_truncate(title, SERP_TITLE_DESKTOP_DISPLAY_MAX),
        title_mobile=_truncate(title, SERP_TITLE_MOBILE_DISPLAY_MAX),
        description_desktop=_truncate(description, SERP_DESCRIPTION_DESKTOP_DISPLAY_MAX),
        description_mobile=_truncate(description, SERP_DESCRIPTION_MOBILE_DISPLAY_MAX),
        warnings=warnings,
        sources={
            "title": title_source,
            "description": description_source,
            "url": url_source,
        },
    )

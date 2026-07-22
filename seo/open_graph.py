"""Open Graph — fallback vrednosti, validacija slika i preview podaci."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

from blogs.models import BlogPost
from core.models import CMSPage
from seo.canonical import build_absolute_canonical
from seo.constants import (
    DEFAULT_BLOG_OG_TYPE,
    DEFAULT_PAGE_OG_TYPE,
    META_DESCRIPTION_MAX_LENGTH,
    OG_IMAGE_ALLOWED_FORMATS,
    OG_IMAGE_MAX_BYTES,
    OG_IMAGE_MIN_HEIGHT,
    OG_IMAGE_MIN_WIDTH,
    OG_IMAGE_RECOMMENDED_HEIGHT,
    OG_IMAGE_RECOMMENDED_WIDTH,
    SEO_TITLE_MAX_LENGTH,
    OgType,
)
from seo.helpers import get_image_dimensions, resolve_absolute_url
from seo.media import get_page_seo_image


class ValidationStatus(StrEnum):
    GOOD = "good"
    OK = "ok"
    BAD = "bad"
    NEUTRAL = "neutral"


@dataclass
class OgImageValidation:
    is_valid: bool
    status: ValidationStatus
    messages: list[str] = field(default_factory=list)
    width: int | None = None
    height: int | None = None
    format_name: str = ""
    file_size: int = 0

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "status": self.status.value,
            "messages": self.messages,
            "width": self.width,
            "height": self.height,
            "format_name": self.format_name,
            "file_size": self.file_size,
        }


@dataclass
class OpenGraphTags:
    og_type: str
    og_title: str
    og_description: str
    og_url: str
    og_image: str
    og_image_width: int | None = None
    og_image_height: int | None = None
    og_image_alt: str = ""
    og_site_name: str = ""
    sources: dict[str, str] = field(default_factory=dict)
    image_validation: OgImageValidation | None = None

    def to_dict(self) -> dict:
        return {
            "og_type": self.og_type,
            "og_title": self.og_title,
            "og_description": self.og_description,
            "og_url": self.og_url,
            "og_image": self.og_image,
            "og_image_width": self.og_image_width,
            "og_image_height": self.og_image_height,
            "og_image_alt": self.og_image_alt,
            "og_site_name": self.og_site_name,
            "sources": self.sources,
            "image_validation": self.image_validation.to_dict()
            if self.image_validation
            else None,
        }


def get_default_og_type(content_object) -> str:
    from education.models import Education
    from treatments.models import Treatment

    if isinstance(content_object, BlogPost):
        return DEFAULT_BLOG_OG_TYPE
    if isinstance(content_object, (Education, Treatment)):
        return OgType.ARTICLE
    if isinstance(content_object, CMSPage):
        return DEFAULT_PAGE_OG_TYPE
    return OgType.WEBSITE


def resolve_og_type(content_object, metadata=None, *, view_og_type: str | None = None) -> str:
    from seo.services import get_seo_metadata

    metadata = metadata if metadata is not None else get_seo_metadata(content_object)
    if metadata and metadata.og_type:
        return metadata.og_type
    if view_og_type:
        return view_og_type
    return get_default_og_type(content_object)


def resolve_og_url(content_object, request=None, metadata=None) -> str:
    from seo.services import get_seo_metadata, resolve_canonical_url

    metadata = metadata if metadata is not None else get_seo_metadata(content_object)
    if metadata and metadata.og_url.strip():
        return metadata.og_url.strip()
    return resolve_canonical_url(content_object, request, metadata) or ""


def resolve_og_title(content_object, metadata=None) -> tuple[str, str]:
    from seo.services import get_seo_metadata, resolve_seo_title

    metadata = metadata if metadata is not None else get_seo_metadata(content_object)
    if metadata and metadata.og_title.strip():
        return metadata.og_title.strip(), "manual"
    return resolve_seo_title(content_object, metadata), "fallback"


def resolve_og_description(content_object, metadata=None) -> tuple[str, str]:
    from seo.services import get_seo_metadata, resolve_meta_description

    metadata = metadata if metadata is not None else get_seo_metadata(content_object)
    if metadata and metadata.og_description.strip():
        return metadata.og_description.strip(), "manual"
    return resolve_meta_description(content_object, metadata), "fallback"


def validate_og_image_file(image_field) -> OgImageValidation:
    """Validira OG sliku — format, veličina fajla i dimenzije."""
    if not image_field or not getattr(image_field, "name", ""):
        return OgImageValidation(
            is_valid=True,
            status=ValidationStatus.NEUTRAL,
            messages=["No custom image — fallback is used."],
        )

    file_size = 0
    try:
        file_size = image_field.size
    except Exception:
        pass

    if file_size and file_size > OG_IMAGE_MAX_BYTES:
        max_mb = OG_IMAGE_MAX_BYTES // (1024 * 1024)
        return OgImageValidation(
            is_valid=False,
            status=ValidationStatus.BAD,
            messages=[f"Image is too large. Maximum is {max_mb} MB."],
            file_size=file_size,
        )

    try:
        image_field.open("rb")
        with Image.open(image_field) as image:
            image.verify()
        image_field.seek(0)
        with Image.open(image_field) as image:
            width, height = image.size
            format_name = (image.format or "").upper()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return OgImageValidation(
            is_valid=False,
            status=ValidationStatus.BAD,
            messages=[f"Image is invalid or corrupted: {exc}"],
            file_size=file_size,
        )
    finally:
        if hasattr(image_field, "close"):
            try:
                image_field.close()
            except Exception:
                pass

    messages: list[str] = []
    status = ValidationStatus.GOOD

    if format_name and format_name not in OG_IMAGE_ALLOWED_FORMATS:
        return OgImageValidation(
            is_valid=False,
            status=ValidationStatus.BAD,
            messages=[
                f"Format {format_name} is not supported. Use JPEG, PNG, or WebP."
            ],
            width=width,
            height=height,
            format_name=format_name,
            file_size=file_size,
        )

    if width < OG_IMAGE_MIN_WIDTH or height < OG_IMAGE_MIN_HEIGHT:
        return OgImageValidation(
            is_valid=False,
            status=ValidationStatus.BAD,
            messages=[
                f"Image is too small ({width}×{height}px). "
                f"Minimum is {OG_IMAGE_MIN_WIDTH}×{OG_IMAGE_MIN_HEIGHT}px."
            ],
            width=width,
            height=height,
            format_name=format_name,
            file_size=file_size,
        )

    if width >= OG_IMAGE_RECOMMENDED_WIDTH and height >= OG_IMAGE_RECOMMENDED_HEIGHT:
        messages.append(
            f"Excellent dimensions ({width}×{height}px)."
        )
    else:
        status = ValidationStatus.OK
        messages.append(
            f"Dimensions {width}×{height}px — recommended "
            f"{OG_IMAGE_RECOMMENDED_WIDTH}×{OG_IMAGE_RECOMMENDED_HEIGHT}px."
        )

    ratio = width / height if height else 0
    ideal_ratio = OG_IMAGE_RECOMMENDED_WIDTH / OG_IMAGE_RECOMMENDED_HEIGHT
    if abs(ratio - ideal_ratio) > 0.35:
        status = ValidationStatus.OK
        messages.append("Aspect ratio is not optimal (recommended ~1.91:1).")

    return OgImageValidation(
        is_valid=True,
        status=status,
        messages=messages,
        width=width,
        height=height,
        format_name=format_name,
        file_size=file_size,
    )


def validate_og_image_field_on_model(instance) -> None:
    if not instance.og_image:
        return
    result = validate_og_image_file(instance.og_image)
    if not result.is_valid:
        raise ValidationError({"og_image": result.messages})


def resolve_og_image(
    content_object,
    request=None,
    metadata=None,
    *,
    visible_only: bool = True,
) -> tuple[str, int | None, int | None, str, OgImageValidation | None]:
    from seo.services import get_seo_metadata

    metadata = metadata if metadata is not None else get_seo_metadata(content_object)

    if metadata and metadata.og_image and getattr(metadata.og_image, "name", ""):
        validation = validate_og_image_file(metadata.og_image)
        url = resolve_absolute_url(request, metadata.og_image.url)
        width, height = get_image_dimensions(metadata.og_image)
        return url or "", width, height, "manual", validation

    url, width, height = get_page_seo_image(content_object, request, visible_only=visible_only)
    if url:
        validation = OgImageValidation(
            is_valid=True,
            status=ValidationStatus.OK,
            messages=["Koristi se istaknuta slika ili slika iz buildera."],
            width=width,
            height=height,
        )
        source = "featured" if getattr(content_object, "featured_image", None) else "builder"
        return url, width, height, source, validation

    from django.conf import settings

    default_og = getattr(settings, "SEO_DEFAULT_OG_IMAGE_URL", "")
    if default_og:
        absolute = build_absolute_canonical(default_og, request) or default_og
        return absolute, None, None, "default", None

    return "", None, None, "none", None


def build_open_graph_tags(
    content_object,
    request=None,
    metadata=None,
    *,
    view_og_type: str | None = None,
    visible_only: bool = True,
    overrides: dict | None = None,
) -> OpenGraphTags:
    from seo.services import get_seo_metadata

    overrides = overrides or {}
    metadata = metadata if metadata is not None else get_seo_metadata(content_object)

    og_title, title_source = resolve_og_title(content_object, metadata)
    og_description, description_source = resolve_og_description(content_object, metadata)
    if overrides.get("og_title"):
        og_title = overrides["og_title"].strip()
        title_source = "manual"
    if overrides.get("og_description"):
        og_description = overrides["og_description"].strip()
        description_source = "manual"

    og_type = overrides.get("og_type") or resolve_og_type(
        content_object,
        metadata,
        view_og_type=view_og_type,
    )
    og_url = overrides.get("og_url") or resolve_og_url(content_object, request, metadata)
    type_source = "fallback"
    if overrides.get("og_type"):
        type_source = "manual"
    elif metadata and metadata.og_type:
        type_source = "manual"
    url_source = "fallback"
    if overrides.get("og_url"):
        url_source = "manual"
    elif metadata and metadata.og_url.strip():
        url_source = "manual"

    og_image, width, height, image_source, image_validation = resolve_og_image(
        content_object,
        request,
        metadata,
        visible_only=visible_only,
    )

    from django.conf import settings

    site_name = getattr(settings, "SEO_SITE_NAME", "Cementne košuljice Ivkov")

    return OpenGraphTags(
        og_type=og_type,
        og_title=og_title[:SEO_TITLE_MAX_LENGTH] if og_title else "",
        og_description=og_description[:META_DESCRIPTION_MAX_LENGTH] if og_description else "",
        og_url=og_url,
        og_image=og_image or "",
        og_image_width=width,
        og_image_height=height,
        og_image_alt=og_title,
        og_site_name=site_name,
        sources={
            "og_type": type_source,
            "og_title": title_source,
            "og_description": description_source,
            "og_url": url_source,
            "og_image": image_source,
        },
        image_validation=image_validation,
    )

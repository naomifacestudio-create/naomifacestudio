"""Twitter Card — fallback vrednosti, validacija slika i preview podaci."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.core.exceptions import ValidationError

from seo.constants import (
    META_DESCRIPTION_MAX_LENGTH,
    SEO_TITLE_MAX_LENGTH,
    TwitterCardType,
)
from seo.helpers import resolve_absolute_url
from seo.open_graph import (
    OgImageValidation,
    OpenGraphTags,
    ValidationStatus,
    build_open_graph_tags,
    validate_og_image_file,
)


@dataclass
class TwitterCardTags:
    twitter_card: str
    twitter_title: str
    twitter_description: str
    twitter_image: str
    sources: dict[str, str] = field(default_factory=dict)
    image_validation: OgImageValidation | None = None

    def to_dict(self) -> dict:
        return {
            "twitter_card": self.twitter_card,
            "twitter_title": self.twitter_title,
            "twitter_description": self.twitter_description,
            "twitter_image": self.twitter_image,
            "sources": self.sources,
            "image_validation": self.image_validation.to_dict()
            if self.image_validation
            else None,
        }


def resolve_twitter_title(
    content_object,
    metadata=None,
    *,
    og_tags: OpenGraphTags | None = None,
) -> tuple[str, str]:
    from seo.services import get_seo_metadata

    metadata = metadata if metadata is not None else get_seo_metadata(content_object)
    if metadata and metadata.twitter_title.strip():
        return metadata.twitter_title.strip(), "manual"
    if og_tags and og_tags.og_title:
        return og_tags.og_title, "og"
    from seo.services import resolve_seo_title

    return resolve_seo_title(content_object, metadata), "fallback"


def resolve_twitter_description(
    content_object,
    metadata=None,
    *,
    og_tags: OpenGraphTags | None = None,
) -> tuple[str, str]:
    from seo.services import get_seo_metadata

    metadata = metadata if metadata is not None else get_seo_metadata(content_object)
    if metadata and metadata.twitter_description.strip():
        return metadata.twitter_description.strip(), "manual"
    if og_tags and og_tags.og_description:
        return og_tags.og_description, "og"
    from seo.services import resolve_meta_description

    return resolve_meta_description(content_object, metadata), "fallback"


def resolve_twitter_card_type(
    content_object,
    metadata=None,
    *,
    has_image: bool = False,
) -> tuple[str, str]:
    from seo.services import get_seo_metadata

    metadata = metadata if metadata is not None else get_seo_metadata(content_object)
    if metadata and metadata.twitter_card and metadata.twitter_card != TwitterCardType.AUTO:
        return metadata.twitter_card, "manual"
    if has_image:
        return TwitterCardType.SUMMARY_LARGE_IMAGE, "fallback"
    return TwitterCardType.SUMMARY, "fallback"


def validate_twitter_image_field_on_model(instance) -> None:
    if not instance.twitter_image:
        return
    result = validate_og_image_file(instance.twitter_image)
    if not result.is_valid:
        raise ValidationError({"twitter_image": result.messages})


def resolve_twitter_image(
    content_object,
    request=None,
    metadata=None,
    *,
    og_tags: OpenGraphTags | None = None,
    visible_only: bool = True,
) -> tuple[str, str, OgImageValidation | None]:
    from seo.services import get_seo_metadata

    metadata = metadata if metadata is not None else get_seo_metadata(content_object)

    if metadata and metadata.twitter_image and getattr(metadata.twitter_image, "name", ""):
        validation = validate_og_image_file(metadata.twitter_image)
        url = resolve_absolute_url(request, metadata.twitter_image.url)
        return url or "", "manual", validation

    if metadata and metadata.og_image and getattr(metadata.og_image, "name", ""):
        validation = validate_og_image_file(metadata.og_image)
        url = resolve_absolute_url(request, metadata.og_image.url)
        if url:
            return url, "og", validation

    if og_tags and og_tags.og_image:
        source = og_tags.sources.get("og_image", "fallback")
        return og_tags.og_image, source, og_tags.image_validation

    from seo.media import get_page_seo_image

    url, _, _ = get_page_seo_image(content_object, request, visible_only=visible_only)
    if url:
        validation = OgImageValidation(
            is_valid=True,
            status=ValidationStatus.OK,
            messages=["Koristi se istaknuta slika ili slika iz buildera."],
        )
        source = "featured" if getattr(content_object, "featured_image", None) else "builder"
        return url, source, validation

    from django.conf import settings

    default_image = getattr(settings, "SEO_DEFAULT_OG_IMAGE_URL", "")
    if default_image:
        from seo.canonical import build_absolute_canonical

        absolute = build_absolute_canonical(default_image, request) or default_image
        return absolute, "default", None

    return "", "none", None


def build_twitter_card_tags(
    content_object,
    request=None,
    metadata=None,
    *,
    og_tags: OpenGraphTags | None = None,
    visible_only: bool = True,
    overrides: dict | None = None,
) -> TwitterCardTags:
    from seo.services import get_seo_metadata

    overrides = overrides or {}
    metadata = metadata if metadata is not None else get_seo_metadata(content_object)

    if og_tags is None and content_object is not None:
        og_tags = build_open_graph_tags(
            content_object,
            request,
            metadata,
            visible_only=visible_only,
            overrides={
                key: overrides[key]
                for key in ("og_title", "og_description")
                if overrides.get(key)
            },
        )

    twitter_title, title_source = resolve_twitter_title(
        content_object,
        metadata,
        og_tags=og_tags,
    )
    twitter_description, description_source = resolve_twitter_description(
        content_object,
        metadata,
        og_tags=og_tags,
    )

    if overrides.get("twitter_title"):
        twitter_title = overrides["twitter_title"].strip()
        title_source = "manual"
    if overrides.get("twitter_description"):
        twitter_description = overrides["twitter_description"].strip()
        description_source = "manual"

    twitter_image, image_source, image_validation = resolve_twitter_image(
        content_object,
        request,
        metadata,
        og_tags=og_tags,
        visible_only=visible_only,
    )

    card_source = "fallback"
    if overrides.get("twitter_card"):
        twitter_card = overrides["twitter_card"]
        card_source = "manual"
    elif metadata and metadata.twitter_card and metadata.twitter_card != TwitterCardType.AUTO:
        twitter_card = metadata.twitter_card
        card_source = "manual"
    else:
        twitter_card, card_source = resolve_twitter_card_type(
            content_object,
            metadata,
            has_image=bool(twitter_image),
        )

    if twitter_card == TwitterCardType.SUMMARY_LARGE_IMAGE and not twitter_image:
        twitter_card = TwitterCardType.SUMMARY
        card_source = "fallback"

    return TwitterCardTags(
        twitter_card=twitter_card,
        twitter_title=twitter_title[:SEO_TITLE_MAX_LENGTH] if twitter_title else "",
        twitter_description=twitter_description[:META_DESCRIPTION_MAX_LENGTH]
        if twitter_description
        else "",
        twitter_image=twitter_image or "",
        sources={
            "twitter_card": card_source,
            "twitter_title": title_source,
            "twitter_description": description_source,
            "twitter_image": image_source,
        },
        image_validation=image_validation,
    )

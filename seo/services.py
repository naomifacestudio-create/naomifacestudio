import json
from urllib.parse import urlsplit, urlunsplit

from django.contrib.contenttypes.models import ContentType
from django.utils import translation
from django.utils.html import strip_tags


def current_locale():
    language = (translation.get_language() or "hr").lower().replace("_", "-")
    if language.startswith("en"):
        return "en"
    # Treat leftover Serbian cookies/locales as Croatian after the locale restore.
    return "hr"


def seo_locale(locale=None):
    language = (locale or current_locale() or "hr").lower().replace("_", "-")
    if language.startswith("en"):
        return "en"
    return "hr"


def get_metadata(obj, locale=None, create=False):
    from .models import SeoMetadata

    locale = seo_locale(locale)
    content_type = ContentType.objects.get_for_model(obj)
    lookup = {
        "content_type": content_type,
        "object_id": obj.pk,
        "locale": locale,
    }
    if create:
        return SeoMetadata.objects.get_or_create(**lookup)[0]
    return SeoMetadata.objects.filter(**lookup).first()


def _absolute_url(request, value):
    value = str(value or "")
    if not value:
        return ""
    if request and value.startswith("/"):
        return request.build_absolute_uri(value)
    return value


def _canonical_url(obj, request, metadata):
    canonical = metadata.canonical_url if metadata and metadata.canonical_url else ""
    if not canonical:
        relative = obj.get_absolute_url(current_locale())
        canonical = request.build_absolute_uri(relative) if request else relative
    if canonical.startswith(("http://", "https://")):
        parts = urlsplit(canonical)
        canonical = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    return canonical


def _default_share_image(request=None):
    from django.templatetags.static import static

    relative = static("images/naomi_first_image_home.webp")
    return _absolute_url(request, relative) if request else relative


def _is_admin_preview(request):
    return bool(
        request
        and request.GET.get("preview") == "1"
        and getattr(request, "user", None)
        and request.user.is_staff
    )


def build_seo_context(obj, request=None):
    locale = current_locale()
    metadata = get_metadata(obj, locale)
    title = metadata.seo_title if metadata and metadata.seo_title else obj.get_title(locale)
    description = (
        metadata.meta_description
        if metadata and metadata.meta_description
        else obj.get_excerpt(locale) or obj.get_body_plaintext(locale)[:320]
    )
    description = strip_tags(description)
    canonical = _canonical_url(obj, request, metadata)

    image = metadata.og_image if metadata and metadata.og_image else getattr(obj, "thumbnail", None)
    image_url = _absolute_url(request, image.url if image else "") or _default_share_image(request)
    twitter_image = (
        _absolute_url(request, metadata.twitter_image.url)
        if metadata and metadata.twitter_image
        else image_url
    )

    published = getattr(obj, "publish_date", None) or getattr(obj, "created_at", None)
    modified = getattr(obj, "updated_at", None)
    schema = {
        "@context": "https://schema.org",
        "@type": metadata.schema_type if metadata and metadata.schema_type else "Article",
        "headline": title,
        "description": description,
        "url": canonical,
    }
    if published:
        schema["datePublished"] = published.isoformat()
    if modified:
        schema["dateModified"] = modified.isoformat()
    if image_url:
        schema["image"] = image_url

    page = obj.get_body_page(locale) or {}
    faq_items = []
    for section in page.get("sections", []):
        for row in section.get("rows", []):
            for column in row.get("columns", []):
                for block in column.get("blocks", []):
                    if block.get("type") == "faq":
                        faq_items.extend((block.get("attrs") or {}).get("items") or [])
    if faq_items:
        schema["mainEntity"] = [
            {
                "@type": "Question",
                "name": item.get("question", ""),
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": item.get("answer", ""),
                },
            }
            for item in faq_items
            if item.get("question") and item.get("answer")
        ]

    alternates = {}
    for alternate_locale in ("hr", "en"):
        with translation.override(alternate_locale):
            alternate_url = obj.get_absolute_url(alternate_locale)
        alternates[alternate_locale] = (
            request.build_absolute_uri(alternate_url) if request else alternate_url
        )

    robots = metadata.robots if metadata else "index, follow"
    if _is_admin_preview(request):
        robots = "noindex, nofollow"

    return {
        "title": title,
        "description": description,
        "canonical": canonical,
        "robots": robots,
        "og_title": metadata.og_title if metadata and metadata.og_title else title,
        "og_description": (
            metadata.og_description
            if metadata and metadata.og_description
            else description
        ),
        "og_image": image_url,
        "og_type": metadata.og_type if metadata and metadata.og_type else "article",
        "og_url": metadata.og_url if metadata and metadata.og_url else canonical,
        "twitter_title": (
            metadata.twitter_title if metadata and metadata.twitter_title else title
        ),
        "twitter_description": (
            metadata.twitter_description
            if metadata and metadata.twitter_description
            else description
        ),
        "twitter_image": twitter_image,
        "twitter_card": (
            metadata.twitter_card
            if metadata and metadata.twitter_card
            else "summary_large_image"
        ),
        "alternates": alternates,
        "x_default": alternates["hr"],
        "schema_json": json.dumps(schema, ensure_ascii=False),
    }

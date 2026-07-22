import json
from urllib.parse import urlsplit, urlunsplit

from django.contrib.contenttypes.models import ContentType
from django.utils import translation
from django.utils.html import strip_tags

from core.locales import normalize_content_locale, seo_locale_for


def current_locale():
    return normalize_content_locale()


def seo_locale(locale=None):
    """Map public content locales onto persisted SEO profiles (1:1)."""
    return seo_locale_for(locale)


def get_metadata(obj, locale=None, create=False):
    from .models import SeoMetadata

    locale = seo_locale(locale)
    content_type = ContentType.objects.get_for_model(obj)
    lookup = {"content_type": content_type, "object_id": obj.pk, "locale": locale}
    return (
        SeoMetadata.objects.get_or_create(**lookup)[0]
        if create
        else SeoMetadata.objects.filter(**lookup).first()
    )


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


def _iso_date(value):
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _published_at(obj):
    published = getattr(obj, "publish_date", None)
    if published is not None:
        return published
    created = getattr(obj, "created_at", None)
    if created is None:
        return None
    return created.date() if hasattr(created, "date") else created


def _modified_at(obj):
    return getattr(obj, "updated_at", None) or getattr(obj, "created_at", None)


def build_seo_context(obj, request=None):
    locale = current_locale()
    metadata = get_metadata(obj, locale)
    title = metadata.seo_title if metadata and metadata.seo_title else obj.get_title(locale)
    description = (
        metadata.meta_description
        if metadata and metadata.meta_description
        else obj.get_excerpt(locale) or (obj.get_body_plaintext(locale) or "")[:320]
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

    schema_type = (
        metadata.schema_type if metadata and metadata.schema_type else "Article"
    )
    schema = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "headline": title,
        "name": title,
        "description": description,
        "url": canonical,
        "datePublished": _iso_date(_published_at(obj)),
        "dateModified": _iso_date(_modified_at(obj)),
    }
    if image_url:
        schema["image"] = image_url

    page = obj.get_body_page(locale) if hasattr(obj, "get_body_page") else {}
    page = page or {}
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

    default_og_type = "product" if schema_type == "Product" else "article"
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
        "og_type": (
            metadata.og_type
            if metadata and metadata.og_type
            else default_og_type
        ),
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


# --- Cement-compatible helpers (keep get_metadata / build_seo_context above) ---


def get_seo_metadata(content_object):
    """Return SEO row if present — does not auto-create."""
    if content_object is None or not getattr(content_object, "pk", None):
        return None

    attached = getattr(content_object, "_seo_analysis_metadata", None)
    if attached is not None:
        return attached

    locale = getattr(content_object, "_seo_locale", None)
    if locale:
        return get_metadata(content_object, locale=locale, create=False)

    from .models import SeoMetadata

    content_types = [
        ContentType.objects.get_for_model(content_object, for_concrete_model=False),
    ]
    concrete_model = content_object._meta.concrete_model
    if concrete_model is not content_object._meta.model:
        content_types.append(
            ContentType.objects.get_for_model(concrete_model, for_concrete_model=True)
        )

    return (
        SeoMetadata.objects.filter(
            content_type__in=content_types,
            object_id=content_object.pk,
        )
        .select_related("content_type")
        .order_by("-pk")
        .first()
    )


def get_default_schema_type(content_object) -> str:
    from blogs.models import Blog, BlogPost
    from education.models import Education
    from seo.constants import DEFAULT_BLOG_SCHEMA, SeoSchemaType
    from treatments.models import Treatment

    if isinstance(content_object, (Blog, BlogPost)):
        return DEFAULT_BLOG_SCHEMA
    if isinstance(content_object, (Education, Treatment)):
        return SeoSchemaType.ARTICLE
    return SeoSchemaType.WEB_PAGE


def resolve_schema_type(content_object, metadata=None) -> str:
    from seo.schema.builders import resolve_effective_schema_type

    return resolve_effective_schema_type(content_object, metadata)


def get_seo_fallback_title(content_object) -> str:
    locale = getattr(content_object, "_seo_locale", None)
    if hasattr(content_object, "get_title"):
        return str(content_object.get_title(locale) or "").strip()
    return str(getattr(content_object, "title", "") or "").strip()


def get_seo_fallback_description(content_object) -> str:
    from seo.content_text import get_content_plain_text

    locale = getattr(content_object, "_seo_locale", None)
    excerpt = getattr(content_object, "excerpt", "") or ""
    if not excerpt and hasattr(content_object, "get_excerpt"):
        excerpt = content_object.get_excerpt(locale) or ""
    if excerpt and str(excerpt).strip():
        return str(excerpt).strip()

    if hasattr(content_object, "get_body_plaintext"):
        plaintext = content_object.get_body_plaintext(locale) or ""
        if plaintext.strip():
            return plaintext.strip()[:320]

    return get_content_plain_text(content_object)


def get_seo_fallback_canonical_path(content_object) -> str | None:
    if hasattr(content_object, "get_absolute_url"):
        url = content_object.get_absolute_url()
        if url:
            return url
    return None


def resolve_seo_title(content_object, metadata=None) -> str:
    metadata = metadata if metadata is not None else get_seo_metadata(content_object)
    if metadata and metadata.seo_title.strip():
        return metadata.seo_title.strip()
    return get_seo_fallback_title(content_object)


def resolve_meta_description(content_object, metadata=None) -> str:
    metadata = metadata if metadata is not None else get_seo_metadata(content_object)
    if metadata and metadata.meta_description.strip():
        return metadata.meta_description.strip()
    return get_seo_fallback_description(content_object)


def resolve_canonical_url(content_object, request=None, metadata=None) -> str | None:
    from seo.canonical import resolve_content_canonical

    metadata = metadata if metadata is not None else get_seo_metadata(content_object)
    return resolve_content_canonical(content_object, request, metadata)


def resolve_breadcrumb_title(content_object, metadata=None) -> str:
    metadata = metadata if metadata is not None else get_seo_metadata(content_object)
    if metadata and metadata.breadcrumb_title.strip():
        return metadata.breadcrumb_title.strip()
    return resolve_seo_title(content_object, metadata)


def resolve_keywords(metadata) -> str:
    if metadata is None:
        return ""
    keywords = list(metadata.secondary_keywords_list)
    if metadata.focus_keyword.strip():
        keywords.insert(0, metadata.focus_keyword.strip())
    return ", ".join(dict.fromkeys(keywords))


def refresh_seo_scores(instance) -> None:
    """Recompute SEO / keyword / readability scores; fall back to zeros on errors."""
    content_object = instance.content_object
    if content_object is None:
        instance.seo_score = 0
        instance.keyword_score = 0
        instance.readability_score = 0
        instance.internal_linking_score = 0
        instance.image_seo_score = 0
        return

    locale = getattr(instance, "locale", None)
    if locale:
        try:
            from seo.host_adapter import adapt_content_for_seo

            content_object = adapt_content_for_seo(
                content_object, locale=locale, metadata=instance
            )
        except Exception:
            pass

    try:
        from seo.scoring import ResolvedSeoScores, compute_seo_score

        resolved = ResolvedSeoScores(
            title=resolve_seo_title(content_object, instance),
            description=resolve_meta_description(content_object, instance),
            focus_keyword=instance.focus_keyword,
            canonical=resolve_canonical_url(content_object, None, instance) or "",
            og_image=instance.og_image.url if instance.og_image else "",
            twitter_image=instance.twitter_image.url if instance.twitter_image else "",
            robots_index=instance.robots_index,
        )
        instance.seo_score = compute_seo_score(
            resolved,
            content_object=content_object,
            metadata=instance,
        )
    except Exception:
        instance.seo_score = 0

    try:
        from seo.readability_analyzer import analyze_readability_for_object

        instance.readability_score = analyze_readability_for_object(
            content_object, visible_only=False
        ).score
    except Exception:
        instance.readability_score = 0

    try:
        from seo.keyword_analyzer import analyze_content_object

        instance.keyword_score = analyze_content_object(
            content_object, instance, visible_only=False
        ).score
    except Exception:
        instance.keyword_score = 0

    try:
        from seo.internal_linking import analyze_internal_linking

        instance.internal_linking_score = analyze_internal_linking(
            content_object, instance, visible_only=False
        ).score
    except Exception:
        instance.internal_linking_score = 0

    try:
        from seo.image_seo import analyze_image_seo

        instance.image_seo_score = analyze_image_seo(
            content_object, instance, visible_only=False
        ).score
    except Exception:
        instance.image_seo_score = 0


SEO_SCORE_UPDATE_FIELDS = (
    "seo_score",
    "keyword_score",
    "readability_score",
    "internal_linking_score",
    "image_seo_score",
    "updated_at",
)


def persist_seo_scores_for_content(content_object):
    """
    Recompute and persist stored SEO scores for an existing SeoMetadata row.
    No-op when the content object has no SEO metadata.
    """
    metadata = get_seo_metadata(content_object)
    if metadata is None:
        return None

    metadata.save(update_fields=list(SEO_SCORE_UPDATE_FIELDS))
    return metadata


def supports_seo(content_object) -> bool:
    return hasattr(content_object, "get_seo_context") and (
        hasattr(content_object, "title") or hasattr(content_object, "get_title")
    )

"""Schema.org builderi — Organization, Person, Article, WebPage, FAQPage, BreadcrumbList."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from django.conf import settings
from django.templatetags.static import static
from django.utils import timezone

from blogs.models import BlogPost
from core.models import CMSPage
from seo.constants import DEFAULT_BLOG_SCHEMA, DEFAULT_PAGE_SCHEMA, SeoSchemaType
from seo.schema.base import (
    JSON_LD_CONTEXT,
    absolute_url,
    clean_schema,
    home_absolute_url,
    organization_logo_url,
    organization_site_url,
)
from seo.schema.faq import extract_faq_items


def resolve_effective_schema_type(content_object, metadata=None) -> str:
    from education.models import Education
    from seo.services import get_seo_metadata
    from treatments.models import Treatment

    metadata = metadata if metadata is not None else get_seo_metadata(content_object)
    if metadata and metadata.schema_type and metadata.schema_type != SeoSchemaType.AUTO:
        return metadata.schema_type

    if isinstance(content_object, BlogPost):
        return DEFAULT_BLOG_SCHEMA
    if isinstance(content_object, (Education, Treatment)):
        return SeoSchemaType.ARTICLE
    if isinstance(content_object, CMSPage):
        return DEFAULT_PAGE_SCHEMA
    return SeoSchemaType.WEB_PAGE


def build_organization_schema(request) -> dict[str, Any] | None:
    name = getattr(settings, "SEO_SITE_NAME", "Naomi Face Studio")
    url = organization_site_url(request)
    if not name or not url:
        return None

    schema: dict[str, Any] = {
        "@context": JSON_LD_CONTEXT,
        "@type": "Organization",
        "@id": f"{url}#organization",
        "name": name,
        "url": url,
    }

    logo = organization_logo_url(request)
    if logo:
        schema["logo"] = {
            "@type": "ImageObject",
            "url": logo,
        }

    phone = getattr(settings, "CONTACT_PHONE", "")
    phone_2 = getattr(settings, "CONTACT_PHONE_2", "")
    phones = [value.strip() for value in (phone, phone_2) if value and value.strip()]
    if len(phones) == 1:
        schema["telephone"] = phones[0]
    elif phones:
        schema["telephone"] = phones

    email = getattr(settings, "SEO_ORGANIZATION_EMAIL", "")
    if email:
        schema["email"] = email

    schema["areaServed"] = {
        "@type": "Country",
        "name": "Serbia",
    }

    return clean_schema(schema)


def build_person_schema(
    request,
    *,
    name: str | None = None,
    url: str | None = None,
    image_url: str | None = None,
    job_title: str | None = None,
) -> dict[str, Any] | None:
    person_name = (
        name
        or getattr(settings, "SEO_PERSON_NAME", "")
        or getattr(settings, "SEO_BLOG_AUTHOR_NAME", "")
        or getattr(settings, "SEO_SITE_NAME", "")
    ).strip()
    if not person_name:
        return None

    person_url = url or getattr(settings, "SEO_PERSON_URL", "") or organization_site_url(request)
    schema: dict[str, Any] = {
        "@context": JSON_LD_CONTEXT,
        "@type": "Person",
        "name": person_name,
    }
    if person_url:
        schema["url"] = person_url
        schema["@id"] = f"{person_url}#person"

    image = image_url or getattr(settings, "SEO_PERSON_IMAGE", "")
    if image:
        schema["image"] = absolute_url(request, image)

    title = job_title or getattr(settings, "SEO_PERSON_JOB_TITLE", "")
    if title:
        schema["jobTitle"] = title

    return clean_schema(schema)


def _author_entity(request) -> dict[str, Any]:
    author_type = getattr(settings, "SEO_BLOG_AUTHOR_TYPE", "Organization").strip()
    if author_type.lower() == "person":
        person = build_person_schema(request)
        if person:
            return {
                "@type": "Person",
                "name": person.get("name"),
                "url": person.get("url"),
            }

    author_name = getattr(
        settings,
        "SEO_BLOG_AUTHOR_NAME",
        getattr(settings, "SEO_SITE_NAME", "Cementne košuljice Ivkov"),
    )
    org = build_organization_schema(request)
    if org:
        return {
            "@type": "Organization",
            "name": author_name or org.get("name"),
            "url": org.get("url"),
        }
    return {"@type": "Organization", "name": author_name}


def build_article_schema(
    request,
    content_object,
    *,
    schema_type: str,
    metadata=None,
) -> dict[str, Any] | None:
    if not isinstance(content_object, BlogPost):
        return None

    from seo.services import resolve_meta_description, resolve_seo_title, resolve_canonical_url

    headline = (
        content_object.get_seo_title()
        if hasattr(content_object, "get_seo_title")
        else resolve_seo_title(content_object, metadata)
    )
    description = (
        content_object.get_seo_description()
        if hasattr(content_object, "get_seo_description")
        else resolve_meta_description(content_object, metadata)
    )
    url = (
        content_object.get_canonical_url(request)
        if hasattr(content_object, "get_canonical_url")
        else resolve_canonical_url(content_object, request, metadata)
    )
    if not headline or not url:
        return None

    from seo.media import get_page_seo_image

    image_url, _, _ = get_page_seo_image(content_object, request)
    published = timezone.make_aware(
        datetime.combine(content_object.publish_date, time.min),
        timezone.get_current_timezone(),
    )
    modified = content_object.updated_at or published

    schema: dict[str, Any] = {
        "@context": JSON_LD_CONTEXT,
        "@type": schema_type,
        "@id": f"{url}#{schema_type.lower()}",
        "headline": headline,
        "description": description,
        "datePublished": published.isoformat(),
        "dateModified": modified.isoformat(),
        "author": _author_entity(request),
        "url": url,
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": url,
        },
    }

    if image_url:
        schema["image"] = [image_url]

    from seo.reading_time import iso_duration_minutes, reading_time_for_content_object

    schema["timeRequired"] = iso_duration_minutes(reading_time_for_content_object(content_object))

    publisher = build_organization_schema(request)
    if publisher:
        schema["publisher"] = {
            "@type": "Organization",
            "name": publisher.get("name"),
            "logo": publisher.get("logo"),
        }

    return clean_schema(schema)


def build_webpage_schema(
    request,
    content_object,
    *,
    schema_type: str = SeoSchemaType.WEB_PAGE,
    metadata=None,
) -> dict[str, Any] | None:
    if not isinstance(content_object, CMSPage):
        return None

    from seo.services import resolve_meta_description, resolve_seo_title, resolve_canonical_url

    name = (
        content_object.get_seo_title()
        if hasattr(content_object, "get_seo_title")
        else resolve_seo_title(content_object, metadata)
    )
    description = (
        content_object.get_seo_description()
        if hasattr(content_object, "get_seo_description")
        else resolve_meta_description(content_object, metadata)
    )
    url = (
        content_object.get_canonical_url(request)
        if hasattr(content_object, "get_canonical_url")
        else resolve_canonical_url(content_object, request, metadata)
    )
    if not name or not url:
        return None

    from seo.media import get_page_seo_image

    site_name = getattr(settings, "SEO_SITE_NAME", "Cementne košuljice Ivkov")
    site_url = organization_site_url(request)

    schema: dict[str, Any] = {
        "@context": JSON_LD_CONTEXT,
        "@type": schema_type,
        "@id": f"{url}#{schema_type.lower()}",
        "name": name,
        "description": description,
        "url": url,
        "inLanguage": "sr-Latn",
        "isPartOf": {
            "@type": "WebSite",
            "name": site_name,
            "url": site_url,
        },
    }

    image_url, _, _ = get_page_seo_image(content_object, request)
    if image_url:
        schema["primaryImageOfPage"] = image_url

    return clean_schema(schema)


def build_faqpage_schema(
    request,
    content_object,
    *,
    metadata=None,
    visible_only: bool = True,
) -> dict[str, Any] | None:
    url = content_object.get_canonical_url(request) if hasattr(content_object, "get_canonical_url") else None
    name = content_object.get_seo_title() if hasattr(content_object, "get_seo_title") else ""
    faq_items = extract_faq_items(content_object, visible_only=visible_only)
    return build_faqpage_schema_from_items(
        request,
        faq_items=faq_items,
        page_url=url,
        name=name,
    )


def build_faqpage_schema_from_items(
    request,
    *,
    faq_items: list,
    page_url: str | None = None,
    name: str | None = None,
) -> dict[str, Any] | None:
    url = page_url or home_absolute_url(request)
    if not url or not faq_items:
        return None

    schema: dict[str, Any] = {
        "@context": JSON_LD_CONTEXT,
        "@type": "FAQPage",
        "@id": f"{url}#faqpage",
        "url": url,
        "mainEntity": [
            {
                "@type": "Question",
                "name": item.question,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": item.answer,
                },
            }
            for item in faq_items
        ],
    }
    if name:
        schema["name"] = name

    return clean_schema(schema)


def build_breadcrumb_schema(
    request,
    content_object,
    *,
    breadcrumb_trail=None,
) -> dict[str, Any] | None:
    from seo.breadcrumbs import resolve_breadcrumb_trail, trail_to_breadcrumb_schema

    trail = breadcrumb_trail or resolve_breadcrumb_trail(request, seo_object=content_object)
    page_url = None
    if content_object is not None and hasattr(content_object, "get_canonical_url"):
        page_url = content_object.get_canonical_url(request)
    return trail_to_breadcrumb_schema(request, trail, page_url=page_url)


def build_primary_schema(
    request,
    content_object,
    *,
    schema_type: str | None = None,
    metadata=None,
    visible_only: bool = True,
) -> dict[str, Any] | None:
    resolved = schema_type or resolve_effective_schema_type(content_object, metadata)

    if resolved in {SeoSchemaType.ARTICLE, SeoSchemaType.BLOG_POSTING}:
        return build_article_schema(
            request,
            content_object,
            schema_type=resolved,
            metadata=metadata,
        )

    if resolved == SeoSchemaType.FAQ_PAGE:
        return build_faqpage_schema(
            request,
            content_object,
            metadata=metadata,
            visible_only=visible_only,
        )

    if resolved == SeoSchemaType.PERSON:
        url = content_object.get_canonical_url(request) if hasattr(content_object, "get_canonical_url") else None
        from seo.media import get_page_seo_image

        image_url, _, _ = get_page_seo_image(content_object, request, visible_only=visible_only)
        person = build_person_schema(request, url=url, image_url=image_url)
        if person and url:
            person["mainEntityOfPage"] = url
        return person

    if resolved == SeoSchemaType.WEB_PAGE:
        if isinstance(content_object, BlogPost):
            return build_article_schema(
                request,
                content_object,
                schema_type=SeoSchemaType.ARTICLE,
                metadata=metadata,
            )
        return build_webpage_schema(
            request,
            content_object,
            schema_type=SeoSchemaType.WEB_PAGE,
            metadata=metadata,
        )

    if resolved == SeoSchemaType.ORGANIZATION:
        return build_organization_schema(request)

    if isinstance(content_object, BlogPost):
        return build_article_schema(
            request,
            content_object,
            schema_type=SeoSchemaType.BLOG_POSTING,
            metadata=metadata,
        )

    if isinstance(content_object, CMSPage):
        return build_webpage_schema(
            request,
            content_object,
            schema_type=SeoSchemaType.WEB_PAGE,
            metadata=metadata,
        )

    return None


def build_homepage_webpage_schema(
    request,
    *,
    title: str,
    description: str,
    page_url: str | None = None,
    image_url: str | None = None,
) -> dict[str, Any] | None:
    """WebPage schema za statičku početnu stranicu."""
    site_name = getattr(settings, "SEO_SITE_NAME", "Cementne košuljice Ivkov")
    site_url = organization_site_url(request)
    url = page_url or home_absolute_url(request)
    if not title or not url:
        return None

    schema: dict[str, Any] = {
        "@context": JSON_LD_CONTEXT,
        "@type": "WebPage",
        "@id": f"{url}#webpage",
        "name": title,
        "description": description,
        "url": url,
        "inLanguage": "sr-Latn",
        "isPartOf": {
            "@type": "WebSite",
            "@id": f"{site_url}#website" if site_url else None,
            "name": site_name,
            "url": site_url,
        },
    }

    if image_url:
        schema["primaryImageOfPage"] = image_url

    publisher = build_organization_schema(request)
    if publisher:
        schema["publisher"] = {
            "@type": "Organization",
            "@id": publisher.get("@id"),
            "name": publisher.get("name"),
            "logo": publisher.get("logo"),
        }

    return clean_schema(schema)


def build_homepage_local_business_schema(
    request,
    *,
    description: str,
    page_url: str | None = None,
    image_url: str | None = None,
) -> dict[str, Any] | None:
    """LocalBusiness schema za statičku početnu stranicu."""
    name = getattr(settings, "SEO_SITE_NAME", "Cementne košuljice Ivkov")
    url = page_url or home_absolute_url(request)
    if not name or not url:
        return None

    schema: dict[str, Any] = {
        "@context": JSON_LD_CONTEXT,
        "@type": "HomeAndConstructionBusiness",
        "@id": f"{url}#localbusiness",
        "name": name,
        "url": url,
        "description": description,
        "areaServed": {
            "@type": "Country",
            "name": "Serbia",
        },
    }

    phone = getattr(settings, "CONTACT_PHONE", "")
    phone_2 = getattr(settings, "CONTACT_PHONE_2", "")
    phones = [value.strip() for value in (phone, phone_2) if value and value.strip()]
    if len(phones) == 1:
        schema["telephone"] = phones[0]
    elif phones:
        schema["telephone"] = phones

    logo = organization_logo_url(request)
    if image_url:
        schema["image"] = image_url
    elif logo:
        schema["image"] = logo

    return clean_schema(schema)


def build_homepage_schema_graph(request) -> list[dict[str, Any]]:
    """JSON-LD graf za statičku početnu stranicu."""
    try:
        from apps.frontend.home_data import (
            HOME_FAQ_ITEMS,
            HOME_OG_IMAGE_STATIC,
            HOME_SEO_DESCRIPTION,
            HOME_SEO_TITLE,
        )
    except ImportError:
        return []

    from seo.schema.faq import FaqItem

    try:
        image_url = absolute_url(request, static(HOME_OG_IMAGE_STATIC))
        page_url = home_absolute_url(request)
    except Exception:
        return []

    schemas: list[dict[str, Any]] = []

    organization = build_organization_schema(request)
    if organization:
        schemas.append(organization)

    webpage = build_homepage_webpage_schema(
        request,
        title=HOME_SEO_TITLE,
        description=HOME_SEO_DESCRIPTION,
        image_url=image_url,
    )
    if webpage:
        schemas.append(webpage)

    local_business = build_homepage_local_business_schema(
        request,
        description=HOME_SEO_DESCRIPTION,
        image_url=image_url,
    )
    if local_business:
        schemas.append(local_business)

    faq_items = [
        FaqItem(question=item["question"], answer=item["answer"])
        for item in HOME_FAQ_ITEMS
    ]
    faq_schema = build_faqpage_schema_from_items(
        request,
        faq_items=faq_items,
        page_url=page_url,
        name="Česta pitanja",
    )
    if faq_schema:
        schemas.append(faq_schema)

    return [schema for schema in schemas if schema]

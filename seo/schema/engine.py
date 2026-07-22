"""Schema.org engine — sastavljanje grafa šema za stranicu."""

from __future__ import annotations

from typing import Any

from blogs.models import BlogPost
from core.models import CMSPage
from seo.constants import SeoSchemaType
from seo.schema.base import serialize_json_ld
from seo.schema.builders import (
    build_breadcrumb_schema,
    build_homepage_schema_graph,
    build_organization_schema,
    build_primary_schema,
    resolve_effective_schema_type,
)
from seo.schema.validation import SchemaValidationResult, validate_schema_graph


def build_schema_graph(
    request,
    content_object,
    *,
    metadata=None,
    schema_type: str | None = None,
    visible_only: bool = True,
    breadcrumb_trail=None,
) -> list[dict[str, Any]]:
    """Vraća listu Schema.org dict-ova pre serijalizacije."""
    if content_object is None:
        organization = build_organization_schema(request)
        return [organization] if organization else []

    resolved_type = schema_type or resolve_effective_schema_type(content_object, metadata)
    schemas: list[dict[str, Any]] = []

    organization = build_organization_schema(request)
    primary = build_primary_schema(
        request,
        content_object,
        schema_type=resolved_type,
        metadata=metadata,
        visible_only=visible_only,
    )

    if resolved_type == SeoSchemaType.ORGANIZATION:
        if organization:
            schemas.append(organization)
    else:
        if organization and resolved_type not in {SeoSchemaType.PERSON}:
            schemas.append(organization)
        if primary:
            schemas.append(primary)

    breadcrumbs = build_breadcrumb_schema(
        request,
        content_object,
        breadcrumb_trail=breadcrumb_trail,
    )
    if breadcrumbs:
        schemas.append(breadcrumbs)

    if isinstance(content_object, (BlogPost, CMSPage)):
        faq_as_primary = resolved_type == SeoSchemaType.FAQ_PAGE
        if not faq_as_primary:
            faq_schema = build_primary_schema(
                request,
                content_object,
                schema_type=SeoSchemaType.FAQ_PAGE,
                metadata=metadata,
                visible_only=visible_only,
            )
            if faq_schema and faq_schema not in schemas:
                schemas.append(faq_schema)

    return [schema for schema in schemas if schema]


def serialize_schema_graph(schemas: list[dict[str, Any]]) -> list[str]:
    return serialize_json_ld(schemas)


def _is_home_request(request) -> bool:
    match = getattr(request, "resolver_match", None)
    return bool(
        match
        and match.app_name == "frontend"
        and match.url_name == "home"
    )


def collect_json_ld_schemas(
    request,
    *,
    seo_object=None,
    metadata=None,
    schema_type: str | None = None,
    visible_only: bool = True,
    breadcrumb_trail=None,
    breadcrumbs_override: list[dict] | None = None,
) -> list[str]:
    """Sastavlja validne JSON-LD stringove za <script type=\"application/ld+json\">."""
    from seo.breadcrumbs import resolve_breadcrumb_trail

    trail = breadcrumb_trail or resolve_breadcrumb_trail(
        request,
        seo_object=seo_object,
        breadcrumbs_override=breadcrumbs_override,
    )

    if seo_object is None:
        if _is_home_request(request):
            return serialize_schema_graph(build_homepage_schema_graph(request))

        schemas = build_schema_graph(request, None, breadcrumb_trail=trail)
        organization = build_organization_schema(request)
        if organization and not any(s.get("@type") == "Organization" for s in schemas):
            schemas.insert(0, organization)
        breadcrumb_schema = build_breadcrumb_schema(
            request,
            None,
            breadcrumb_trail=trail,
        )
        if breadcrumb_schema:
            schemas.append(breadcrumb_schema)
        return serialize_schema_graph(schemas)

    if isinstance(seo_object, CMSPage) and not seo_object.is_active:
        return serialize_schema_graph(build_schema_graph(request, None, breadcrumb_trail=trail))

    from seo.services import get_seo_metadata

    metadata = metadata if metadata is not None else get_seo_metadata(seo_object)
    schemas = build_schema_graph(
        request,
        seo_object,
        metadata=metadata,
        schema_type=schema_type,
        visible_only=visible_only,
        breadcrumb_trail=trail,
    )
    return serialize_schema_graph(schemas)


def preview_schema_bundle(
    request,
    content_object,
    *,
    metadata=None,
    schema_type: str | None = None,
    visible_only: bool = False,
) -> tuple[list[dict[str, Any]], list[str], SchemaValidationResult]:
    """Pomoćnik za admin preview — raw šeme, JSON stringovi i validacija."""
    schemas = build_schema_graph(
        request,
        content_object,
        metadata=metadata,
        schema_type=schema_type,
        visible_only=visible_only,
    )
    payloads = serialize_schema_graph(schemas)
    requested = schema_type or resolve_effective_schema_type(content_object, metadata)
    validation = validate_schema_graph(
        schemas,
        content_object=content_object,
        requested_type=requested,
    )
    return schemas, payloads, validation

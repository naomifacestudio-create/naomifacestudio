"""JSON-LD structured data — kompatibilnost sa starim importima."""

from __future__ import annotations

from typing import Any

from seo.schema.base import JSON_LD_CONTEXT, clean_schema, serialize_json_ld
from seo.schema.builders import (
    build_article_schema as build_blog_posting_schema,
    build_breadcrumb_schema as build_blog_breadcrumb_schema,
    build_organization_schema,
    build_webpage_schema,
)
from seo.schema.engine import build_schema_graph, collect_json_ld_schemas

__all__ = (
    "JSON_LD_CONTEXT",
    "build_blog_breadcrumb_schema",
    "build_blog_posting_schema",
    "build_organization_schema",
    "build_schema_graph",
    "build_webpage_schema",
    "clean_schema",
    "collect_json_ld_schemas",
    "serialize_json_ld",
)

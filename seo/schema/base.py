"""Zajedničke pomoćne funkcije za Schema.org JSON-LD."""

from __future__ import annotations

import json
from typing import Any

from django.conf import settings
from django.templatetags.static import static

JSON_LD_CONTEXT = "https://schema.org"


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, dict):
        cleaned_dict = {}
        for key, nested in value.items():
            nested_value = clean_value(nested)
            if nested_value is not None:
                cleaned_dict[key] = nested_value
        return cleaned_dict or None
    if isinstance(value, list):
        cleaned_list = []
        for item in value:
            nested_value = clean_value(item)
            if nested_value is not None:
                cleaned_list.append(nested_value)
        return cleaned_list or None
    return value


def clean_schema(schema: dict[str, Any]) -> dict[str, Any] | None:
    if not schema:
        return None

    cleaned = clean_value(schema)
    if not isinstance(cleaned, dict):
        return None
    if cleaned.get("@context") != JSON_LD_CONTEXT or not cleaned.get("@type"):
        return None
    return cleaned


def absolute_url(request, path_or_url: str | None) -> str | None:
    if not path_or_url:
        return None
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url
    if request:
        try:
            return request.build_absolute_uri(path_or_url)
        except Exception:
            pass
    base = getattr(settings, "SITE_BASE_URL", "").rstrip("/")
    if base and path_or_url.startswith("/"):
        return f"{base}{path_or_url}"
    return path_or_url


def organization_site_url(request) -> str | None:
    configured = getattr(settings, "SITE_BASE_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    if request:
        return request.build_absolute_uri("/").rstrip("/")
    return None


def reverse_home_path() -> str:
    """Resolve site home path across Naomi (`core:home`) and sibling projects."""
    from django.urls import NoReverseMatch, reverse

    for name in ("core:home", "home", "frontend:home"):
        try:
            return reverse(name)
        except NoReverseMatch:
            continue
    return "/"


def home_absolute_url(request) -> str | None:
    return absolute_url(request, reverse_home_path()) or organization_site_url(request)


def organization_logo_url(request) -> str | None:
    logo_path = getattr(
        settings,
        "SEO_ORGANIZATION_LOGO",
        getattr(settings, "SITE_ADMIN_BRAND_LOGO", "img/logo.webp"),
    )
    return absolute_url(request, static(logo_path))


def serialize_json_ld(schemas: list[dict[str, Any]]) -> list[str]:
    serialized: list[str] = []
    for schema in schemas:
        cleaned = clean_schema(schema)
        if cleaned is None:
            continue
        try:
            json_text = json.dumps(cleaned, ensure_ascii=False, separators=(",", ":"))
            json.loads(json_text)
        except (TypeError, ValueError):
            continue
        json_text = json_text.replace("<", "\\u003c")
        serialized.append(json_text)
    return serialized

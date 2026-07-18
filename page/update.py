"""Ažuriranje page sadržaja na host objektu (BlogPost)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from page.constants import PAGE_FORMAT_V1
from page.normalize import normalize_page
from page.plaintext import extract_page_plaintext
from page.validation import validate_page_or_raise


class PageVersionConflictError(Exception):
    def __init__(self, expected: int, actual: int):
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Konflikt verzije stranice: očekivano {expected}, trenutno {actual}."
        )


@dataclass(frozen=True)
class PageUpdateResult:
    changed: bool
    page_version: int


def pages_are_equal(left: Any, right: Any) -> bool:
    return _canonical_json(left) == _canonical_json(right)


def apply_body_page_update(
    host,
    page: dict[str, Any],
    *,
    expected_version: int | None = None,
) -> PageUpdateResult:
    if expected_version is not None and host.page_version != expected_version:
        raise PageVersionConflictError(expected_version, host.page_version)

    page = normalize_page(page)
    validate_page_or_raise(page)

    if pages_are_equal(host.body_page, page):
        return PageUpdateResult(
            changed=False,
            page_version=host.page_version,
        )

    from core.json_media import (
        cleanup_removed_json_media,
        extract_media_refs_from_page,
    )

    old_refs = extract_media_refs_from_page(host.body_page) if host.body_page else set()
    new_refs = extract_media_refs_from_page(page)
    cleanup_removed_json_media(old_refs, new_refs)

    host.body_page = page
    host.body_plaintext = extract_page_plaintext(page)
    if hasattr(host, "body_format"):
        host.body_format = PAGE_FORMAT_V1
    host.page_version += 1

    return PageUpdateResult(
        changed=True,
        page_version=host.page_version,
    )


def apply_localized_page_update(host, locale, page, *, expected_version=None):
    """Validate and save one locale without touching the other translations."""
    from core.content import LOCALE_SUFFIX

    if locale not in LOCALE_SUFFIX:
        raise KeyError(f"Unsupported builder locale: {locale}")
    suffix = LOCALE_SUFFIX[locale]
    page_field = f"body_page{suffix}"
    text_field = f"body_plaintext{suffix}"
    version_field = f"page_version{suffix}"
    actual = getattr(host, version_field)
    if expected_version is not None and actual != expected_version:
        raise PageVersionConflictError(expected_version, actual)
    page = normalize_page(page)
    validate_page_or_raise(page)
    old_page = getattr(host, page_field)
    if pages_are_equal(old_page, page):
        return PageUpdateResult(False, actual)

    from core.json_media import cleanup_removed_json_media, extract_media_refs_from_page

    old_refs = extract_media_refs_from_page(old_page)
    new_refs = extract_media_refs_from_page(page)
    setattr(host, page_field, page)
    setattr(host, text_field, extract_page_plaintext(page))
    setattr(host, version_field, actual + 1)
    host.save(update_fields=[page_field, text_field, version_field, "updated_at"])
    cleanup_removed_json_media(old_refs, new_refs)
    return PageUpdateResult(True, actual + 1)


def _canonical_json(value: Any) -> str:
    if value is None:
        return "null"
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

"""Validacija JSON-LD prema Google Rich Results preporukama."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from seo.schema.faq import extract_faq_items


class CheckStatus(StrEnum):
    GOOD = "good"
    OK = "ok"
    BAD = "bad"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class SchemaValidationCheck:
    schema_type: str
    field: str
    label: str
    status: CheckStatus
    message: str


@dataclass
class SchemaValidationResult:
    score: int = 0
    checks: list[SchemaValidationCheck] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    schema_types: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "checks": [
                {
                    "schema_type": check.schema_type,
                    "field": check.field,
                    "label": check.label,
                    "status": check.status.value,
                    "message": check.message,
                }
                for check in self.checks
            ],
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "schema_types": self.schema_types,
        }


def _add_check(
    checks: list[SchemaValidationCheck],
    *,
    schema_type: str,
    field: str,
    label: str,
    status: CheckStatus,
    message: str,
) -> None:
    checks.append(
        SchemaValidationCheck(
            schema_type=schema_type,
            field=field,
            label=label,
            status=status,
            message=message,
        )
    )


def _has_publisher_logo(schema: dict[str, Any]) -> bool:
    publisher = schema.get("publisher")
    if not isinstance(publisher, dict):
        return False
    logo = publisher.get("logo")
    if isinstance(logo, dict):
        return bool(logo.get("url"))
    return bool(logo)


def _validate_article_like(schema: dict[str, Any], checks: list[SchemaValidationCheck]) -> None:
    schema_type = schema.get("@type", "Article")

    if schema.get("headline"):
        _add_check(
            checks,
            schema_type=schema_type,
            field="headline",
            label="Headline",
            status=CheckStatus.GOOD,
            message="Headline is present.",
        )
    else:
        _add_check(
            checks,
            schema_type=schema_type,
            field="headline",
            label="Headline",
            status=CheckStatus.BAD,
            message="Google requires a headline for articles.",
        )

    if schema.get("datePublished"):
        _add_check(
            checks,
            schema_type=schema_type,
            field="datePublished",
            label="Datum objave",
            status=CheckStatus.GOOD,
            message="datePublished is set.",
        )
    else:
        _add_check(
            checks,
            schema_type=schema_type,
            field="datePublished",
            label="Datum objave",
            status=CheckStatus.BAD,
            message="datePublished is missing.",
        )

    author = schema.get("author")
    if isinstance(author, dict) and author.get("name"):
        _add_check(
            checks,
            schema_type=schema_type,
            field="author",
            label="Autor",
            status=CheckStatus.GOOD,
            message=f"Autor: {author.get('name')}.",
        )
    else:
        _add_check(
            checks,
            schema_type=schema_type,
            field="author",
            label="Autor",
            status=CheckStatus.BAD,
            message="Google recommends an author with a name.",
        )

    if _has_publisher_logo(schema):
        _add_check(
            checks,
            schema_type=schema_type,
            field="publisher.logo",
            label="Publisher logo",
            status=CheckStatus.GOOD,
            message="Publisher ima logo (ImageObject).",
        )
    else:
        _add_check(
            checks,
            schema_type=schema_type,
            field="publisher.logo",
            label="Publisher logo",
            status=CheckStatus.OK,
            message="Add an organization logo for Article rich results.",
        )

    image = schema.get("image")
    if image:
        _add_check(
            checks,
            schema_type=schema_type,
            field="image",
            label="Image",
            status=CheckStatus.GOOD,
            message="Article image is present.",
        )
    else:
        _add_check(
            checks,
            schema_type=schema_type,
            field="image",
            label="Image",
            status=CheckStatus.OK,
            message="Google recommends an image for Article rich results.",
        )


def _validate_webpage(schema: dict[str, Any], checks: list[SchemaValidationCheck]) -> None:
    schema_type = schema.get("@type", "WebPage")

    if schema.get("name") and schema.get("url"):
        _add_check(
            checks,
            schema_type=schema_type,
            field="name",
            label="Naziv stranice",
            status=CheckStatus.GOOD,
            message="WebPage ima name i url.",
        )
    else:
        _add_check(
            checks,
            schema_type=schema_type,
            field="name",
            label="Naziv stranice",
            status=CheckStatus.BAD,
            message="WebPage must have name and url.",
        )


def _validate_faqpage(
    schema: dict[str, Any],
    checks: list[SchemaValidationCheck],
) -> None:
    schema_type = "FAQPage"
    main_entity = schema.get("mainEntity")

    if not isinstance(main_entity, list) or not main_entity:
        _add_check(
            checks,
            schema_type=schema_type,
            field="mainEntity",
            label="FAQ pitanja",
            status=CheckStatus.BAD,
            message="FAQPage must have at least one question in mainEntity.",
        )
        return

    valid_questions = 0
    for entity in main_entity:
        if not isinstance(entity, dict):
            continue
        answer = entity.get("acceptedAnswer")
        if entity.get("name") and isinstance(answer, dict) and answer.get("text"):
            valid_questions += 1

    if valid_questions >= 2:
        status = CheckStatus.GOOD
        message = f"Found {valid_questions} valid FAQ items."
    elif valid_questions == 1:
        status = CheckStatus.OK
        message = "Found 1 FAQ item — add more questions."
    else:
        status = CheckStatus.BAD
        message = "FAQ stavke nemaju ispravan Question/Answer format."

    _add_check(
        checks,
        schema_type=schema_type,
        field="mainEntity",
        label="FAQ pitanja",
        status=status,
        message=message,
    )


def _validate_organization(schema: dict[str, Any], checks: list[SchemaValidationCheck]) -> None:
    if schema.get("name") and schema.get("url"):
        _add_check(
            checks,
            schema_type="Organization",
            field="name",
            label="Organizacija",
            status=CheckStatus.GOOD,
            message="Organization ima name i url.",
        )
    else:
        _add_check(
            checks,
            schema_type="Organization",
            field="name",
            label="Organizacija",
            status=CheckStatus.BAD,
            message="Organization must have name and url.",
        )

    logo = schema.get("logo")
    if logo:
        _add_check(
            checks,
            schema_type="Organization",
            field="logo",
            label="Logo",
            status=CheckStatus.GOOD,
            message="Organization logo is present.",
        )
    else:
        _add_check(
            checks,
            schema_type="Organization",
            field="logo",
            label="Logo",
            status=CheckStatus.OK,
            message="Recommended: add an organization logo.",
        )


def _validate_person(schema: dict[str, Any], checks: list[SchemaValidationCheck]) -> None:
    if schema.get("name"):
        _add_check(
            checks,
            schema_type="Person",
            field="name",
            label="Ime",
            status=CheckStatus.GOOD,
            message="Person ima name.",
        )
    else:
        _add_check(
            checks,
            schema_type="Person",
            field="name",
            label="Ime",
            status=CheckStatus.BAD,
            message="Person must have a name.",
        )


def _validate_breadcrumb(schema: dict[str, Any], checks: list[SchemaValidationCheck]) -> None:
    items = schema.get("itemListElement")
    if not isinstance(items, list) or len(items) < 2:
        _add_check(
            checks,
            schema_type="BreadcrumbList",
            field="itemListElement",
            label="Breadcrumb stavke",
            status=CheckStatus.BAD,
            message="BreadcrumbList should have at least 2 items.",
        )
        return

    valid = all(
        isinstance(item, dict)
        and item.get("position")
        and item.get("name")
        and item.get("item")
        for item in items
    )
    _add_check(
        checks,
        schema_type="BreadcrumbList",
        field="itemListElement",
        label="Breadcrumb stavke",
        status=CheckStatus.GOOD if valid else CheckStatus.BAD,
        message="Breadcrumb stavke su validne."
        if valid
        else "Each item must have position, name, and item.",
    )


def _validate_single_schema(schema: dict[str, Any]) -> list[SchemaValidationCheck]:
    checks: list[SchemaValidationCheck] = []
    schema_type = schema.get("@type", "")

    if schema_type in {"Article", "BlogPosting"}:
        _validate_article_like(schema, checks)
    elif schema_type == "WebPage":
        _validate_webpage(schema, checks)
    elif schema_type == "FAQPage":
        _validate_faqpage(schema, checks)
    elif schema_type == "Organization":
        _validate_organization(schema, checks)
    elif schema_type == "Person":
        _validate_person(schema, checks)
    elif schema_type == "BreadcrumbList":
        _validate_breadcrumb(schema, checks)

    return checks


def validate_schema_graph(
    schemas: list[dict[str, Any]],
    *,
    content_object=None,
    requested_type: str = "",
) -> SchemaValidationResult:
    checks: list[SchemaValidationCheck] = []
    warnings: list[str] = []
    recommendations: list[str] = []
    schema_types = [schema.get("@type", "") for schema in schemas if schema.get("@type")]

    for schema in schemas:
        checks.extend(_validate_single_schema(schema))

    if requested_type == "FAQPage" and "FAQPage" not in schema_types:
        faq_count = len(extract_faq_items(content_object)) if content_object else 0
        if faq_count == 0:
            warnings.append(
                "FAQPage is selected, but there are no FAQ items in the builder "
                "(config.items or heading + text pairs)."
            )
            recommendations.append(
                "Add a FAQ block in the builder or use an H2–H4 heading followed by text."
            )
        else:
            warnings.append("FAQPage was not generated — check that the content is saved.")

    if requested_type in {"Article", "BlogPosting"} and not any(
        t in schema_types for t in {"Article", "BlogPosting"}
    ):
        warnings.append("Article/BlogPosting schema was not generated — check title and URL.")

    good = sum(1 for check in checks if check.status == CheckStatus.GOOD)
    ok = sum(1 for check in checks if check.status == CheckStatus.OK)
    bad = sum(1 for check in checks if check.status == CheckStatus.BAD)
    total = len(checks) or 1
    score = max(0, min(100, int(((good * 1.0) + (ok * 0.6) - (bad * 0.5)) / total * 100)))

    if bad == 0 and good >= ok:
        recommendations.append("Structured data meets Google recommendations.")
    elif bad:
        recommendations.append("Fix the red items before publishing.")

    return SchemaValidationResult(
        score=score,
        checks=checks,
        warnings=warnings,
        recommendations=recommendations,
        schema_types=schema_types,
    )

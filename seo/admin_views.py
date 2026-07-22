"""Admin API za live Yoast-style SEO analize."""

from __future__ import annotations

import json

from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from seo.ai_readiness import analyze_ai_readiness
from seo.analysis_ui import (
    render_ai_readiness_html,
    render_cornerstone_analysis_html,
    render_image_seo_html,
    render_internal_linking_html,
    render_keyword_analysis_html,
    render_open_graph_preview_html,
    render_readability_analysis_html,
    render_schema_preview_html,
    render_serp_preview_html,
    render_slug_analysis_html,
    render_twitter_preview_html,
    render_unified_scoring_html,
)
from seo.constants import DEFAULT_OG_PREVIEW_PLATFORM
from seo.image_seo import analyze_image_seo
from seo.serp_preview import build_serp_preview
from seo.unified_scoring import analyze_unified_seo
from seo.content_analysis import ContentAnalysisInput
from seo.cornerstone import analyze_cornerstone_content
from seo.internal_linking import analyze_internal_linking
from seo.keyword_analyzer import analyze_content_object, analyze_keyword_content
from seo.open_graph import OpenGraphTags, build_open_graph_tags
from seo.twitter_card import TwitterCardTags, build_twitter_card_tags
from seo.readability_analyzer import analyze_readability_for_object
from seo.schema.engine import preview_schema_bundle
from seo.schema.validation import SchemaValidationResult
from seo.services import get_seo_metadata
from seo.slug_analyzer import analyze_slug, analyze_slug_for_object
from seo.host_adapter import adapt_content_for_seo


def _apply_live_editor_overrides(content_object, payload: dict) -> None:
    """Primeni nesnimljeno stanje editora na objekat za live SEO analizu."""
    if content_object is None:
        return

    body_plaintext = payload.get("body_plaintext", None)
    if body_plaintext is not None:
        content_object.body_plaintext = body_plaintext or ""

    body_page = payload.get("body_page", None)
    if isinstance(body_page, dict):
        content_object.body_page = body_page


@require_POST
def image_seo_analysis_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    content_object = _load_content_object(payload)
    metadata = get_seo_metadata(content_object) if content_object else None

    _apply_live_editor_overrides(content_object, payload)

    body_page = payload.get("body_page")
    body_page_override = body_page if isinstance(body_page, dict) else None

    if content_object is not None:
        result = analyze_image_seo(
            content_object,
            metadata,
            visible_only=False,
            body_page=body_page_override,
        )
    else:
        from seo.image_seo import ImageSeoResult

        result = ImageSeoResult(
            message="Save the post to run the image analysis.",
        )

    data = result.to_dict()
    data["html"] = render_image_seo_html(result)
    return JsonResponse(data)


@require_POST
def serp_preview_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    content_object = _load_content_object(payload)
    metadata = get_seo_metadata(content_object) if content_object else None
    overrides = _payload_overrides(payload)

    preview = build_serp_preview(
        content_object,
        request,
        metadata,
        overrides=overrides,
    )
    data = preview.to_dict()
    data["html"] = render_serp_preview_html(preview)
    return JsonResponse(data)


@require_POST
def unified_score_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    content_object = _load_content_object(payload)
    metadata = get_seo_metadata(content_object) if content_object else None
    overrides = _payload_overrides(payload)

    _apply_live_editor_overrides(content_object, payload)

    if content_object is not None:
        result = analyze_unified_seo(
            content_object,
            metadata,
            request=request,
            overrides=overrides,
            visible_only=False,
        )
    else:
        from seo.unified_scoring import UnifiedSeoScoreResult

        result = UnifiedSeoScoreResult(
            message="Save the post to see the overall SEO score.",
        )

    data = result.to_dict()
    data["html"] = render_unified_scoring_html(result)
    return JsonResponse(data)


@require_POST
def keyword_analysis_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    content_object = _load_content_object(payload)
    metadata = get_seo_metadata(content_object) if content_object else None
    overrides = _payload_overrides(payload)

    _apply_live_editor_overrides(content_object, payload)

    if content_object is not None:
        result = analyze_content_object(
            content_object,
            metadata,
            overrides=overrides,
            visible_only=False,
        )
    else:
        analysis_input = ContentAnalysisInput(
            article_title=overrides["article_title"].strip(),
            content=overrides.get("content", overrides["excerpt"]).strip(),
            seo_title=overrides["seo_title"].strip() or overrides["article_title"].strip(),
            meta_description=overrides["meta_description"].strip(),
            focus_keyword=overrides["focus_keyword"].strip(),
            h1=overrides["article_title"].strip(),
            first_paragraph=overrides["excerpt"].strip(),
            url_slug=overrides["url_slug"].strip(),
            word_count=len(overrides.get("content", overrides["excerpt"]).split()),
        )
        result = analyze_keyword_content(analysis_input)

    data = result.to_dict()
    data["html"] = render_keyword_analysis_html(result)
    return JsonResponse(data)


@require_POST
def slug_analysis_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    content_object = _load_content_object(payload)
    metadata = get_seo_metadata(content_object) if content_object else None
    overrides = _payload_overrides(payload)

    if content_object is not None:
        result = analyze_slug_for_object(
            content_object,
            metadata,
            overrides=overrides,
        )
    else:
        result = analyze_slug(
            overrides.get("url_slug", ""),
            focus_keyword=overrides.get("focus_keyword", ""),
        )

    data = result.to_dict()
    data["html"] = render_slug_analysis_html(result)
    return JsonResponse(data)


@require_POST
def ai_readiness_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    content_object = _load_content_object(payload)
    metadata = get_seo_metadata(content_object) if content_object else None
    overrides = _payload_overrides(payload)

    _apply_live_editor_overrides(content_object, payload)

    if content_object is not None:
        result = analyze_ai_readiness(
            content_object,
            metadata,
            overrides=overrides,
            visible_only=False,
        )
    else:
        from seo.ai_readiness import AiReadinessResult

        result = AiReadinessResult(
            message="Save the post to see the AI readiness analysis.",
        )

    data = result.to_dict()
    data["html"] = render_ai_readiness_html(result)
    return JsonResponse(data)


@require_POST
def readability_analysis_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    content_object = _load_content_object(payload)
    overrides = {"excerpt": payload.get("excerpt", "")}

    _apply_live_editor_overrides(content_object, payload)

    if content_object is not None:
        result = analyze_readability_for_object(
            content_object,
            overrides=overrides,
            visible_only=False,
        )
    else:
        from seo.readability_analyzer import analyze_readability
        from seo.readability_content import ReadabilityContentInput
        from seo.content_text import normalize_whitespace, split_sentences

        excerpt = overrides.get("excerpt", "").strip()
        content = normalize_whitespace(excerpt)
        result = analyze_readability(
            ReadabilityContentInput(
                content=content,
                sentences=split_sentences(content),
                paragraphs=[content] if content else [],
                headings=[],
                word_count=len(content.split()) if content else 0,
            )
        )

    data = result.to_dict()
    data["html"] = render_readability_analysis_html(result)
    return JsonResponse(data)


@require_POST
def open_graph_preview_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    content_object = _load_content_object(payload)
    metadata = get_seo_metadata(content_object) if content_object else None
    overrides = _payload_overrides(payload)
    overrides["og_title"] = payload.get("og_title", overrides.get("seo_title", ""))
    overrides["og_description"] = payload.get("og_description", overrides.get("meta_description", ""))
    overrides["og_type"] = payload.get("og_type", "")
    overrides["og_url"] = payload.get("og_url", "")

    if content_object is None:
        title = overrides.get("og_title") or overrides.get("seo_title") or overrides.get("article_title", "")
        description = overrides.get("og_description") or overrides.get("meta_description", "")
        tags = OpenGraphTags(
            og_type=overrides.get("og_type") or "website",
            og_title=title,
            og_description=description,
            og_url=overrides.get("og_url", ""),
            og_image="",
            sources={
                "og_title": "manual" if overrides.get("og_title") else "fallback",
                "og_description": "manual" if overrides.get("og_description") else "fallback",
                "og_type": "manual" if overrides.get("og_type") else "fallback",
                "og_url": "manual" if overrides.get("og_url") else "fallback",
                "og_image": "none",
            },
        )
    else:
        tags = build_open_graph_tags(
            content_object,
            request,
            metadata,
            view_og_type=payload.get("view_og_type"),
            visible_only=False,
            overrides=overrides,
        )

    data = tags.to_dict()
    platform = payload.get("platform") or DEFAULT_OG_PREVIEW_PLATFORM
    data["html"] = render_open_graph_preview_html(tags, platform=platform)
    return JsonResponse(data)


@require_POST
def cornerstone_analysis_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    content_object = _load_content_object(payload)
    metadata = get_seo_metadata(content_object) if content_object else None
    overrides = _payload_overrides(payload)
    overrides["is_cornerstone"] = _parse_bool(payload.get("is_cornerstone"))

    _apply_live_editor_overrides(content_object, payload)

    if content_object is not None:
        result = analyze_cornerstone_content(
            content_object,
            metadata,
            overrides=overrides,
            visible_only=False,
        )
    else:
        from seo.cornerstone import CornerstoneAnalysisResult

        result = CornerstoneAnalysisResult(
            message="Save the blog post to see the cornerstone analysis.",
        )

    data = result.to_dict()
    data["html"] = render_cornerstone_analysis_html(result)
    return JsonResponse(data)


@require_POST
def internal_linking_analysis_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    content_object = _load_content_object(payload)
    metadata = get_seo_metadata(content_object) if content_object else None
    overrides = _payload_overrides(payload)

    _apply_live_editor_overrides(content_object, payload)

    if content_object is not None:
        result = analyze_internal_linking(
            content_object,
            metadata,
            overrides=overrides,
            visible_only=False,
        )
    else:
        from seo.internal_linking import InternalLinkingResult

        result = InternalLinkingResult(
            score=0,
            message="Save the blog post to see internal link suggestions.",
        )

    data = result.to_dict()
    data["html"] = render_internal_linking_html(result)
    return JsonResponse(data)


@require_POST
def twitter_card_preview_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    content_object = _load_content_object(payload)
    metadata = get_seo_metadata(content_object) if content_object else None
    overrides = _payload_overrides(payload)
    overrides["twitter_title"] = payload.get("twitter_title", "")
    overrides["twitter_description"] = payload.get("twitter_description", "")
    overrides["twitter_card"] = payload.get("twitter_card", "")
    overrides["og_title"] = payload.get("og_title", overrides.get("seo_title", ""))
    overrides["og_description"] = payload.get(
        "og_description",
        overrides.get("meta_description", ""),
    )

    if content_object is None:
        title = (
            overrides.get("twitter_title")
            or overrides.get("og_title")
            or overrides.get("seo_title")
            or overrides.get("article_title", "")
        )
        description = (
            overrides.get("twitter_description")
            or overrides.get("og_description")
            or overrides.get("meta_description", "")
        )
        card = overrides.get("twitter_card") or "summary"
        tags = TwitterCardTags(
            twitter_card=card,
            twitter_title=title,
            twitter_description=description,
            twitter_image="",
            sources={
                "twitter_card": "manual" if overrides.get("twitter_card") else "fallback",
                "twitter_title": "manual" if overrides.get("twitter_title") else "fallback",
                "twitter_description": "manual"
                if overrides.get("twitter_description")
                else "fallback",
                "twitter_image": "none",
            },
        )
    else:
        og_tags = build_open_graph_tags(
            content_object,
            request,
            metadata,
            visible_only=False,
            overrides={
                key: overrides[key]
                for key in ("og_title", "og_description", "og_type", "og_url")
                if overrides.get(key)
            },
        )
        tags = build_twitter_card_tags(
            content_object,
            request,
            metadata,
            og_tags=og_tags,
            visible_only=False,
            overrides=overrides,
        )

    data = tags.to_dict()
    data["html"] = render_twitter_preview_html(tags)
    return JsonResponse(data)


@require_POST
def schema_preview_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    content_object = _load_content_object(payload)
    metadata = get_seo_metadata(content_object) if content_object else None
    schema_type = payload.get("schema_type", "")

    if content_object is None:
        validation = SchemaValidationResult(
            score=0,
            warnings=["Save the post to see the full JSON-LD preview."],
        )
        data = validation.to_dict()
        data["json_ld"] = []
        data["html"] = render_schema_preview_html(
            schema_types=[],
            json_payloads=[],
            validation=validation,
        )
        return JsonResponse(data)

    _, payloads, validation = preview_schema_bundle(
        request,
        content_object,
        metadata=metadata,
        schema_type=schema_type or None,
        visible_only=False,
    )
    data = validation.to_dict()
    data["json_ld"] = payloads
    data["html"] = render_schema_preview_html(
        schema_types=validation.schema_types,
        json_payloads=payloads,
        validation=validation,
    )
    return JsonResponse(data)


def _payload_overrides(payload: dict) -> dict:
    return {
        "article_title": payload.get("article_title", ""),
        "url_slug": payload.get("url_slug", ""),
        "excerpt": payload.get("excerpt", ""),
        "seo_title": payload.get("seo_title", ""),
        "meta_description": payload.get("meta_description", ""),
        "focus_keyword": payload.get("focus_keyword", ""),
        "canonical_url": payload.get("canonical_url", ""),
    }


def _parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).lower() in {"1", "true", "on", "yes"}


def _load_content_object(payload: dict):
    content_type_id = payload.get("content_type_id")
    object_id = payload.get("object_id")

    if not content_type_id or not object_id:
        return None

    try:
        content_type = ContentType.objects.get(pk=int(content_type_id))
        content_object = content_type.get_object_for_this_type(pk=int(object_id))
    except (ContentType.DoesNotExist, ValueError, TypeError):
        return None

    locale = payload.get("locale")
    if locale:
        from seo.models import SeoMetadata

        ct = ContentType.objects.get_for_model(content_object)
        locale_meta = SeoMetadata.objects.filter(
            content_type=ct,
            object_id=content_object.pk,
            locale=locale,
        ).first()
        return adapt_content_for_seo(
            content_object, locale=locale, metadata=locale_meta
        )

    metadata = get_seo_metadata(content_object)
    if metadata is not None and getattr(metadata, "locale", None):
        return adapt_content_for_seo(
            content_object, locale=metadata.locale, metadata=metadata
        )

    return content_object

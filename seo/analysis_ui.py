"""HTML prikaz Yoast-style SEO analiza u adminu."""

from __future__ import annotations

from django.utils.html import format_html, format_html_join

from seo.keyword_analyzer import CheckStatus as KeywordCheckStatus
from seo.keyword_analyzer import KeywordAnalysisResult
from seo.readability_analyzer import ReadabilityAnalysisResult
from seo.open_graph import OpenGraphTags
from seo.serp_preview import SerpPreview
from seo.cornerstone import CornerstoneAnalysisResult
from seo.image_seo import ImageSeoResult
from seo.internal_linking import InternalLinkingResult
from seo.unified_scoring import UnifiedSeoScoreResult
from seo.constants import DEFAULT_OG_PREVIEW_PLATFORM, OG_PLATFORM_PROFILES
from seo.slug_analyzer import SlugAnalysisResult
from seo.ai_readiness import AiReadinessResult

STATUS_SCORE_CLASS = {
    KeywordCheckStatus.GOOD: "seo-analyzer__score--good",
    KeywordCheckStatus.OK: "seo-analyzer__score--ok",
    KeywordCheckStatus.BAD: "seo-analyzer__score--bad",
    KeywordCheckStatus.NEUTRAL: "seo-analyzer__score--neutral",
}


def score_status_class(score: int) -> str:
    if score >= 70:
        return STATUS_SCORE_CLASS[KeywordCheckStatus.GOOD]
    if score >= 40:
        return STATUS_SCORE_CLASS[KeywordCheckStatus.OK]
    return STATUS_SCORE_CLASS[KeywordCheckStatus.BAD]


def _render_checks_html(checks) -> str:
    return format_html_join(
        "",
        (
            '<li class="seo-analyzer__check seo-analyzer__check--{}">'
            '<span class="seo-analyzer__dot" aria-hidden="true"></span>'
            '<span class="seo-analyzer__check-body">'
            "<strong>{}</strong>"
            '<span class="seo-analyzer__message">{}</span>'
            "</span></li>"
        ),
        (
            (check.status.value, check.label, check.message)
            for check in checks
        ),
    )


def render_keyword_analysis_html(result: KeywordAnalysisResult) -> str:
    score_class = score_status_class(result.score)
    keyword_label = result.focus_keyword or "—"

    return format_html(
        '<div class="seo-analyzer" data-seo-keyword-analyzer>'
        '<div class="seo-analyzer__header">'
        '<div class="seo-analyzer__score {}" data-seo-score-ring>'
        '<span class="seo-analyzer__score-value" data-seo-score-value>{}</span>'
        '<span class="seo-analyzer__score-label">/100</span>'
        "</div>"
        '<div class="seo-analyzer__meta">'
        "<p><strong>Focus keyword:</strong> "
        '<span data-seo-focus-keyword>{}</span></p>'
        '<p class="seo-analyzer__hint">'
        "Analysis updates as you type. Save the post to store the score."
        "</p></div></div>"
        '<ul class="seo-analyzer__checks" data-seo-checks-list>{}</ul>'
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Recommendations</h4>"
        '<ul class="seo-analyzer__recommendations" data-seo-recommendations-list>{}</ul>'
        "</div></div>",
        score_class,
        result.score,
        keyword_label,
        _render_checks_html(result.checks),
        format_html_join(
            "",
            '<li class="seo-analyzer__recommendation">{}</li>',
            ((item,) for item in result.recommendations),
        ),
    )


def render_readability_analysis_html(result: ReadabilityAnalysisResult) -> str:
    score_class = score_status_class(result.score)
    warnings_html = format_html_join(
        "",
        '<li class="seo-analyzer__warning">{}</li>',
        ((item,) for item in result.warnings),
    ) if result.warnings else format_html(
        '<li class="seo-analyzer__warning seo-analyzer__warning--none">No warnings.</li>'
    )

    return format_html(
        '<div class="seo-analyzer" data-seo-readability-analyzer>'
        '<div class="seo-analyzer__header">'
        '<div class="seo-analyzer__score {}" data-seo-score-ring>'
        '<span class="seo-analyzer__score-value" data-seo-score-value>{}</span>'
        '<span class="seo-analyzer__score-label">/100</span>'
        "</div>"
        '<div class="seo-analyzer__meta">'
        "<p><strong>Reading difficulty:</strong> "
        '<span data-seo-difficulty-label>{}</span></p>'
        '<p class="seo-analyzer__hint">'
        "Analysis uses builder content. Save the post to store the score."
        "</p></div></div>"
        '<ul class="seo-analyzer__checks" data-seo-checks-list>{}</ul>'
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Warnings</h4>"
        '<ul class="seo-analyzer__warnings" data-seo-warnings-list>{}</ul>'
        "</div>"
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Recommendations</h4>"
        '<ul class="seo-analyzer__recommendations" data-seo-recommendations-list>{}</ul>'
        "</div></div>",
        score_class,
        result.score,
        result.difficulty_label,
        _render_checks_html(result.checks),
        warnings_html,
        format_html_join(
            "",
            '<li class="seo-analyzer__recommendation">{}</li>',
            ((item,) for item in result.recommendations),
        ),
    )


def render_empty_analysis_html(message: str, *, analyzer_type: str = "keyword") -> str:
    data_attr = {
        "keyword": "data-seo-keyword-analyzer",
        "readability": "data-seo-readability-analyzer",
        "open_graph": "data-seo-og-preview",
        "twitter": "data-seo-twitter-preview",
        "schema": "data-seo-schema-preview",
        "internal_linking": "data-seo-internal-linking-analyzer",
        "cornerstone": "data-seo-cornerstone-analyzer",
        "unified_score": "data-seo-unified-score-analyzer",
        "serp": "data-seo-serp-preview",
        "image_seo": "data-seo-image-seo-analyzer",
        "slug": "data-seo-slug-analyzer",
        "ai_readiness": "data-seo-ai-readiness-analyzer",
    }.get(analyzer_type, "data-seo-keyword-analyzer")
    return format_html(
        '<div class="seo-analyzer seo-analyzer--empty" {}><p>{}</p></div>',
        data_attr,
        message,
    )


def _source_badge(source: str) -> str:
    labels = {
        "manual": "Manual",
        "fallback": "Automatic",
        "featured": "Featured image",
        "builder": "Builder",
        "default": "Default",
        "none": "—",
        "og": "Open Graph",
    }
    return labels.get(source, source)


def render_slug_analysis_html(result: SlugAnalysisResult) -> str:
    if result.message and not result.checks:
        return render_empty_analysis_html(result.message, analyzer_type="slug")

    score_class = score_status_class(result.score)
    slug_label = result.slug or "—"

    return format_html(
        '<div class="seo-analyzer" data-seo-slug-analyzer>'
        '<div class="seo-analyzer__header">'
        '<div class="seo-analyzer__score {}" data-seo-score-ring>'
        '<span class="seo-analyzer__score-value" data-seo-score-value>{}</span>'
        '<span class="seo-analyzer__score-label">/100</span>'
        "</div>"
        '<div class="seo-analyzer__meta">'
        "<p><strong>Slug:</strong> "
        '<code data-seo-slug-value>{}</code></p>'
        "<p><strong>URL preview:</strong> "
        '<span data-seo-slug-preview-url>{}</span></p>'
        '<p class="seo-analyzer__hint">'
        "Analysis updates as you change the slug and focus keyword."
        "</p></div></div>"
        '<ul class="seo-analyzer__checks" data-seo-checks-list>{}</ul>'
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Recommendations</h4>"
        '<ul class="seo-analyzer__recommendations" data-seo-recommendations-list>{}</ul>'
        "</div></div>",
        score_class,
        result.score,
        slug_label,
        result.preview_url or "—",
        _render_checks_html(result.checks),
        format_html_join(
            "",
            '<li class="seo-analyzer__recommendation">{}</li>',
            ((item,) for item in result.recommendations),
        ),
    )


def render_ai_readiness_html(result: AiReadinessResult) -> str:
    if result.message and not result.checks:
        return render_empty_analysis_html(result.message, analyzer_type="ai_readiness")

    score_class = score_status_class(result.score)

    return format_html(
        '<div class="seo-analyzer" data-seo-ai-readiness-analyzer>'
        '<div class="seo-analyzer__header">'
        '<div class="seo-analyzer__score {}" data-seo-score-ring>'
        '<span class="seo-analyzer__score-value" data-seo-score-value>{}</span>'
        '<span class="seo-analyzer__score-label">/100</span>'
        "</div>"
        '<div class="seo-analyzer__meta">'
        "<p><strong>AI readiness</strong> — how understandable the content is "
        "for AI search (Google AI Overviews, ChatGPT, Perplexity).</p>"
        '<p class="seo-analyzer__hint">'
        "Analysis updates as you edit content in the builder."
        "</p></div></div>"
        '<ul class="seo-analyzer__checks" data-seo-checks-list>{}</ul>'
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Recommendations</h4>"
        '<ul class="seo-analyzer__recommendations" data-seo-recommendations-list>{}</ul>'
        "</div></div>",
        score_class,
        result.score,
        _render_checks_html(result.checks),
        format_html_join(
            "",
            '<li class="seo-analyzer__recommendation">{}</li>',
            ((item,) for item in result.recommendations),
        ),
    )


def _truncate_preview_text(text: str, max_length: int) -> str:
    value = (text or "").strip()
    if len(value) <= max_length:
        return value
    return value[: max_length - 1].rstrip() + "…"


def render_open_graph_preview_html(
    tags: OpenGraphTags,
    *,
    platform: str = DEFAULT_OG_PREVIEW_PLATFORM,
) -> str:
    profile = OG_PLATFORM_PROFILES.get(platform, OG_PLATFORM_PROFILES[DEFAULT_OG_PREVIEW_PLATFORM])
    title = _truncate_preview_text(tags.og_title or "Share title", profile["title_max"])
    description = _truncate_preview_text(
        tags.og_description or "Social description",
        profile["description_max"],
    )
    image_block = format_html(
        '<div class="seo-og-preview__image seo-og-preview__image--empty">'
        "<span>No image</span></div>"
    )
    if tags.og_image:
        image_block = format_html(
            '<div class="seo-og-preview__image">'
            '<img src="{}" alt="">'
            "</div>",
            tags.og_image,
        )

    validation_html = ""
    if tags.image_validation and tags.image_validation.messages:
        status = tags.image_validation.status.value
        validation_html = format_html(
            '<ul class="seo-og-preview__validation seo-og-preview__validation--{}">{}</ul>',
            status,
            format_html_join(
                "",
                "<li>{}</li>",
                ((msg,) for msg in tags.image_validation.messages),
            ),
        )

    meta_rows = format_html_join(
        "",
        '<tr><th>{}</th><td><code>{}</code> <span class="seo-og-preview__source">{}</span></td></tr>',
        (
            ("og:title", tags.og_title or "—", _source_badge(tags.sources.get("og_title", ""))),
            ("og:description", tags.og_description[:80] or "—", _source_badge(tags.sources.get("og_description", ""))),
            ("og:type", tags.og_type or "—", _source_badge(tags.sources.get("og_type", ""))),
            ("og:url", tags.og_url or "—", _source_badge(tags.sources.get("og_url", ""))),
            ("og:image", "Yes" if tags.og_image else "No", _source_badge(tags.sources.get("og_image", ""))),
        ),
    )

    tabs_html = format_html_join(
        "",
        (
            '<button type="button" class="seo-og-preview__tab{}" '
            'data-og-platform="{}" aria-pressed="{}">{}</button>'
        ),
        (
            (
                " seo-og-preview__tab--active" if key == platform else "",
                key,
                "true" if key == platform else "false",
                value["label"],
            )
            for key, value in OG_PLATFORM_PROFILES.items()
        ),
    )

    domain = ""
    if tags.og_url:
        domain = tags.og_url.replace("https://", "").replace("http://", "").split("/")[0]
    elif tags.og_site_name:
        domain = tags.og_site_name
    else:
        domain = f"{profile['label']} preview"

    return format_html(
        '<div class="seo-og-preview" data-seo-og-preview data-og-platform="{}">'
        '<div class="seo-og-preview__tabs" role="tablist">{}</div>'
        '<div class="seo-og-preview__card {}">'
        "{}"
        '<div class="seo-og-preview__body">'
        '<p class="seo-og-preview__domain" data-og-preview-domain>{}</p>'
        '<p class="seo-og-preview__title" data-og-preview-title>{}</p>'
        '<p class="seo-og-preview__description" data-og-preview-description>{}</p>'
        "</div></div>"
        "{}"
        '<table class="seo-og-preview__meta"><tbody>{}</tbody></table>'
        "</div>",
        platform,
        tabs_html,
        profile["card_class"],
        image_block,
        domain,
        title,
        description,
        validation_html,
        meta_rows,
    )


def _twitter_card_label(card_type: str) -> str:
    labels = {
        "summary": "Summary",
        "summary_large_image": "Summary large image",
    }
    return labels.get(card_type, card_type or "—")


def render_twitter_preview_html(tags: TwitterCardTags) -> str:
    is_large = tags.twitter_card == "summary_large_image"
    card_class = "seo-twitter-preview__card--large" if is_large else "seo-twitter-preview__card--summary"

    image_block = ""
    if is_large:
        if tags.twitter_image:
            image_block = format_html(
                '<div class="seo-twitter-preview__image">'
                '<img src="{}" alt="">'
                "</div>",
                tags.twitter_image,
            )
        else:
            image_block = format_html(
                '<div class="seo-twitter-preview__image seo-twitter-preview__image--empty">'
                "<span>No image</span></div>"
            )

    validation_html = ""
    if tags.image_validation and tags.image_validation.messages:
        status = tags.image_validation.status.value
        validation_html = format_html(
            '<ul class="seo-twitter-preview__validation seo-twitter-preview__validation--{}">{}</ul>',
            status,
            format_html_join(
                "",
                "<li>{}</li>",
                ((msg,) for msg in tags.image_validation.messages),
            ),
        )

    meta_rows = format_html_join(
        "",
        '<tr><th>{}</th><td><code>{}</code> <span class="seo-twitter-preview__source">{}</span></td></tr>',
        (
            (
                "twitter:card",
                _twitter_card_label(tags.twitter_card),
                _source_badge(tags.sources.get("twitter_card", "")),
            ),
            (
                "twitter:title",
                tags.twitter_title[:80] or "—",
                _source_badge(tags.sources.get("twitter_title", "")),
            ),
            (
                "twitter:description",
                tags.twitter_description[:80] or "—",
                _source_badge(tags.sources.get("twitter_description", "")),
            ),
            (
                "twitter:image",
                "Yes" if tags.twitter_image else "No",
                _source_badge(tags.sources.get("twitter_image", "")),
            ),
        ),
    )

    return format_html(
        '<div class="seo-twitter-preview" data-seo-twitter-preview>'
        '<p class="seo-twitter-preview__badge">Twitter / X Card</p>'
        '<div class="seo-twitter-preview__card {}">'
        "{}"
        '<div class="seo-twitter-preview__body">'
        '<p class="seo-twitter-preview__title" data-twitter-preview-title>{}</p>'
        '<p class="seo-twitter-preview__description" data-twitter-preview-description>{}</p>'
        '<p class="seo-twitter-preview__card-type">{}</p>'
        "</div></div>"
        "{}"
        '<table class="seo-twitter-preview__meta"><tbody>{}</tbody></table>'
        "</div>",
        card_class,
        image_block,
        tags.twitter_title or "Share title",
        tags.twitter_description or "Twitter / X description",
        _twitter_card_label(tags.twitter_card),
        validation_html,
        meta_rows,
    )


def render_schema_preview_html(
    *,
    schema_types: list[str],
    json_payloads: list[str],
    validation: SchemaValidationResult,
) -> str:
    import json as json_module

    score_class = score_status_class(validation.score)
    types_html = format_html_join(
        "",
        '<span class="seo-schema-preview__type">{}</span>',
        ((schema_type,) for schema_type in schema_types),
    ) or format_html('<span class="seo-schema-preview__type seo-schema-preview__type--empty">—</span>')

    checks_html = format_html_join(
        "",
        (
            '<li class="seo-analyzer__check seo-analyzer__check--{}">'
            '<span class="seo-analyzer__dot" aria-hidden="true"></span>'
            '<span class="seo-analyzer__check-body">'
            "<strong>{} · {}</strong>"
            '<span class="seo-analyzer__message">{}</span>'
            "</span></li>"
        ),
        (
            (
                check.status.value,
                check.schema_type,
                check.label,
                check.message,
            )
            for check in validation.checks
        ),
    )

    warnings_html = format_html_join(
        "",
        '<li class="seo-analyzer__warning">{}</li>',
        ((item,) for item in validation.warnings),
    ) if validation.warnings else format_html(
        '<li class="seo-analyzer__warning seo-analyzer__warning--none">No warnings.</li>'
    )

    json_blocks = []
    for payload in json_payloads:
        try:
            pretty = json_module.dumps(
                json_module.loads(payload),
                ensure_ascii=False,
                indent=2,
            )
        except (TypeError, ValueError):
            pretty = payload
        json_blocks.append(
            format_html(
                '<pre class="seo-schema-preview__json"><code>{}</code></pre>',
                pretty,
            )
        )

    json_html = format_html_join("", "{}", ((block,) for block in json_blocks))
    if not json_blocks:
        json_html = format_html(
            '<pre class="seo-schema-preview__json seo-schema-preview__json--empty">'
            "No JSON-LD generated — check title, URL and schema type."
            "</pre>"
        )

    return format_html(
        '<div class="seo-schema-preview" data-seo-schema-preview>'
        '<div class="seo-analyzer__header">'
        '<div class="seo-analyzer__score {}" data-seo-score-ring>'
        '<span class="seo-analyzer__score-value" data-seo-score-value>{}</span>'
        '<span class="seo-analyzer__score-label">/100</span>'
        "</div>"
        '<div class="seo-analyzer__meta">'
        "<p><strong>Schema types:</strong> {}</p>"
        '<p class="seo-analyzer__hint">'
        "Validation against Google Rich Results recommendations. Save the post to apply the type."
        "</p></div></div>"
        '<ul class="seo-analyzer__checks" data-seo-checks-list>{}</ul>'
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Warnings</h4>"
        '<ul class="seo-analyzer__warnings" data-seo-warnings-list>{}</ul>'
        "</div>"
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>JSON-LD</h4>"
        '<div class="seo-schema-preview__json-wrap" data-seo-schema-json>{}</div>'
        "</div></div>",
        score_class,
        validation.score,
        types_html,
        checks_html,
        warnings_html,
        json_html,
    )


def render_internal_linking_html(result: InternalLinkingResult) -> str:
    if result.message and not result.checks:
        return render_empty_analysis_html(result.message, analyzer_type="internal_linking")

    score_class = score_status_class(result.score)
    suggestions_html = format_html_join(
        "",
        (
            '<tr class="seo-internal-linking__row seo-internal-linking__row--{}">'
            "<td><strong>{}</strong></td>"
            "<td><code>{}</code></td>"
            "<td>{}</td>"
            "<td>{}</td>"
            "<td>{}</td>"
            "</tr>"
        ),
        (
            (
                "linked" if item.already_linked else "suggested",
                f"{item.target_title}{' ★ Cornerstone' if item.is_cornerstone else ''}",
                item.target_url,
                item.suggested_anchor,
                item.reason,
                "Linked" if item.already_linked else "Recommended",
            )
            for item in result.link_suggestions
        ),
    )
    if not result.link_suggestions:
        suggestions_html = format_html(
            '<tr><td colspan="5" class="seo-internal-linking__empty">'
            "No suggestions — publish more related posts."
            "</td></tr>"
        )

    existing_html = format_html_join(
        "",
        (
            '<li class="seo-internal-linking__existing">'
            "<strong>{}</strong> → <code>{}</code>"
            '<span class="seo-internal-linking__source">{}</span>'
            "</li>"
        ),
        (
            (
                link.get("anchor_text") or "—",
                link.get("href") or "—",
                link.get("source") or "",
            )
            for link in result.existing_links
        ),
    )
    if not result.existing_links:
        existing_html = format_html(
            '<li class="seo-internal-linking__existing seo-internal-linking__existing--none">'
            "No internal links detected."
            "</li>"
        )

    return format_html(
        '<div class="seo-analyzer seo-internal-linking" data-seo-internal-linking-analyzer>'
        '<div class="seo-analyzer__header">'
        '<div class="seo-analyzer__score {}" data-seo-score-ring>'
        '<span class="seo-analyzer__score-value" data-seo-score-value>{}</span>'
        '<span class="seo-analyzer__score-label">/100</span>'
        "</div>"
        '<div class="seo-analyzer__meta">'
        "<p><strong>Internal links:</strong> "
        '<span data-seo-internal-link-count>{}</span></p>'
        '<p class="seo-analyzer__hint">'
        "Suggestions update from builder content. Save the post to store the score."
        "</p></div></div>"
        '<ul class="seo-analyzer__checks" data-seo-checks-list>{}</ul>'
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Link suggestions</h4>"
        '<table class="seo-internal-linking__table">'
        "<thead><tr>"
        "<th>Post</th><th>URL</th><th>Anchor text</th><th>Reason</th><th>Status</th>"
        "</tr></thead>"
        '<tbody data-seo-link-suggestions>{}</tbody>'
        "</table></div>"
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Existing internal links</h4>"
        '<ul class="seo-internal-linking__existing-list" data-seo-existing-links>{}</ul>'
        "</div>"
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Recommendations</h4>"
        '<ul class="seo-analyzer__recommendations" data-seo-recommendations-list>{}</ul>'
        "</div></div>",
        score_class,
        result.score,
        result.internal_link_count,
        _render_checks_html(result.checks),
        suggestions_html,
        existing_html,
        format_html_join(
            "",
            '<li class="seo-analyzer__recommendation">{}</li>',
            ((item,) for item in result.recommendations),
        ),
    )


def render_cornerstone_analysis_html(result: CornerstoneAnalysisResult) -> str:
    if result.message and not result.checks:
        return render_empty_analysis_html(result.message, analyzer_type="cornerstone")

    score_class = score_status_class(result.score)
    role_label = "Cornerstone post" if result.is_cornerstone else "Supporting post"

    warnings_html = format_html_join(
        "",
        '<li class="seo-analyzer__warning">{}</li>',
        ((item,) for item in result.warnings),
    ) if result.warnings else format_html(
        '<li class="seo-analyzer__warning seo-analyzer__warning--none">No warnings.</li>'
    )

    parent_html = ""
    if not result.is_cornerstone:
        parent_html = format_html(
            '<p class="seo-cornerstone__parent">'
            "<strong>Cornerstone klaster:</strong> "
            '<a href="{}" target="_blank" rel="noopener">{}</a>'
            " · {} · "
            '<span class="seo-cornerstone__parent-status">{}</span>'
            "</p>",
            result.parent_cornerstone["url"],
            result.parent_cornerstone["title"],
            result.parent_cornerstone["reason"],
            "Linked" if result.parent_cornerstone.get("links_to_cornerstone") else "Not linked",
        ) if result.parent_cornerstone else format_html(
            '<p class="seo-cornerstone__parent seo-cornerstone__parent--none">'
            "No cornerstone cluster assigned for this topic."
            "</p>"
        )

    supporting_html = format_html(
        '<tr><td colspan="4" class="seo-cornerstone__empty">'
        "Supporting table is available when the post is marked as cornerstone."
        "</td></tr>"
    )
    if result.is_cornerstone:
        supporting_html = format_html_join(
            "",
            (
                '<tr class="seo-cornerstone__row seo-cornerstone__row--{}">'
                "<td><strong>{}</strong></td>"
                "<td><code>{}</code></td>"
                "<td>{}</td>"
                "<td>{}</td>"
                "</tr>"
            ),
            (
                (
                    "linked" if item.links_to_cornerstone else "missing",
                    item.title,
                    item.url,
                    item.reason,
                    "Links" if item.links_to_cornerstone else "Missing link",
                )
                for item in result.supporting_articles
            ),
        )
        if not result.supporting_articles:
            supporting_html = format_html(
                '<tr><td colspan="4" class="seo-cornerstone__empty">'
                "No supporting posts identified — publish related topics."
                "</td></tr>"
            )

    cluster_html = format_html_join(
        "",
        '<li class="seo-cornerstone__cluster"><strong>{}</strong> — {}</li>',
        (
            (cluster.cornerstone_title, cluster.recommendation)
            for cluster in result.cluster_recommendations
        ),
    )
    if not result.cluster_recommendations:
        cluster_html = format_html(
            '<li class="seo-cornerstone__cluster seo-cornerstone__cluster--none">'
            "Mark cornerstone posts to see cluster recommendations."
            "</li>"
        )

    checks_html = format_html_join(
        "",
        (
            '<li class="seo-analyzer__check seo-analyzer__check--{}">'
            '<span class="seo-analyzer__dot" aria-hidden="true"></span>'
            '<span class="seo-analyzer__check-body">'
            "<strong>{}</strong>"
            '<span class="seo-analyzer__message">{}</span>'
            "</span></li>"
        ),
        (
            (check.status.value, check.label, check.message)
            for check in result.checks
        ),
    )

    return format_html(
        '<div class="seo-analyzer seo-cornerstone" data-seo-cornerstone-analyzer>'
        '<div class="seo-analyzer__header">'
        '<div class="seo-analyzer__score {}" data-seo-score-ring>'
        '<span class="seo-analyzer__score-value" data-seo-score-value>{}</span>'
        '<span class="seo-analyzer__score-label">/100</span>'
        "</div>"
        '<div class="seo-analyzer__meta">'
        "<p><strong>Role:</strong> "
        '<span data-seo-cornerstone-role>{}</span></p>'
        "<p><strong>Incoming links:</strong> "
        '<span data-seo-incoming-count>{}</span></p>'
        '<p class="seo-analyzer__hint">'
        "Mark cornerstones for main topics. Supporting posts should link to them."
        "</p></div></div>"
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Orphan warnings</h4>"
        '<ul class="seo-analyzer__warnings" data-seo-cornerstone-warnings>{}</ul>'
        "</div>"
        '<div class="seo-cornerstone__parent-wrap" data-seo-parent-cornerstone>{}</div>'
        '<ul class="seo-analyzer__checks" data-seo-checks-list>{}</ul>'
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Supporting posts</h4>"
        '<table class="seo-cornerstone__table">'
        "<thead><tr>"
        "<th>Post</th><th>URL</th><th>Reason</th><th>Status</th>"
        "</tr></thead>"
        '<tbody data-seo-supporting-articles>{}</tbody>'
        "</table></div>"
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Cluster recommendations</h4>"
        '<ul class="seo-cornerstone__clusters" data-seo-cluster-recommendations>{}</ul>'
        "</div>"
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Recommendations</h4>"
        '<ul class="seo-analyzer__recommendations" data-seo-recommendations-list>{}</ul>'
        "</div></div>",
        score_class,
        result.score,
        role_label,
        result.incoming_link_count,
        warnings_html,
        parent_html,
        checks_html,
        supporting_html,
        cluster_html,
        format_html_join(
            "",
            '<li class="seo-analyzer__recommendation">{}</li>',
            ((item,) for item in result.recommendations),
        ),
    )


def render_unified_scoring_html(result: UnifiedSeoScoreResult) -> str:
    import json

    if result.message and not result.categories:
        return render_empty_analysis_html(result.message, analyzer_type="unified_score")

    score_class = score_status_class(result.overall_score)
    categories_html = format_html_join(
        "",
        (
            '<tr class="seo-unified-score__row seo-unified-score__row--{}">'
            "<td><strong>{}</strong></td>"
            "<td>{}</td>"
            "<td>{}</td>"
            "<td>{}</td>"
            "</tr>"
        ),
        (
            (
                category.status,
                category.label,
                category.score,
                category.weight,
                category.weighted_contribution,
            )
            for category in result.categories
        ),
    )

    json_payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    return format_html(
        '<div class="seo-analyzer seo-unified-score" data-seo-unified-score-analyzer>'
        '<div class="seo-analyzer__header">'
        '<div class="seo-analyzer__score {}" data-seo-score-ring>'
        '<span class="seo-analyzer__score-value" data-seo-score-value>{}</span>'
        '<span class="seo-analyzer__score-label">/100</span>'
        "</div>"
        '<div class="seo-analyzer__meta">'
        "<p><strong>Overall SEO score</strong> — weighted average of 9 categories.</p>"
        "<p><strong>Focus keyword:</strong> "
        '<span data-seo-focus-keyword>{}</span> · '
        "<strong>Words:</strong> "
        '<span data-seo-word-count>{}</span></p>'
        '<p class="seo-analyzer__hint">'
        "JSON output updates live. Save the post to store seo_score."
        "</p></div></div>"
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Categories</h4>"
        '<table class="seo-unified-score__table">'
        "<thead><tr>"
        "<th>Category</th><th>Score</th><th>Weight</th><th>Contribution</th>"
        "</tr></thead>"
        '<tbody data-seo-category-scores>{}</tbody>'
        "</table></div>"
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Recommendations</h4>"
        '<ul class="seo-analyzer__recommendations" data-seo-recommendations-list>{}</ul>'
        "</div>"
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Machine-readable JSON</h4>"
        '<pre class="seo-unified-score__json" data-seo-unified-json><code>{}</code></pre>'
        "</div></div>",
        score_class,
        result.overall_score,
        result.focus_keyword or "—",
        result.word_count,
        categories_html,
        format_html_join(
            "",
            '<li class="seo-analyzer__recommendation">{}</li>',
            ((item,) for item in result.recommendations),
        ),
        json_payload,
    )


def _serp_result_block(
    *,
    variant: str,
    label: str,
    title: str,
    display_url: str,
    description: str,
) -> str:
    return format_html(
        '<div class="seo-serp-preview__result seo-serp-preview__result--{}" '
        'data-serp-variant="{}">'
        '<p class="seo-serp-preview__variant-label">{}</p>'
        '<div class="seo-serp-preview__snippet">'
        '<p class="seo-serp-preview__title" data-serp-title>{}</p>'
        '<p class="seo-serp-preview__url" data-serp-url>{}</p>'
        '<p class="seo-serp-preview__description" data-serp-description>{}</p>'
        "</div></div>",
        variant,
        variant,
        label,
        title or "Page title",
        display_url or "example.com",
        description or "The page meta description appears here in Google search results.",
    )


def render_serp_preview_html(preview: SerpPreview) -> str:
    warnings_html = format_html_join(
        "",
        (
            '<li class="seo-serp-preview__warning seo-serp-preview__warning--{}">'
            "<strong>{}</strong> "
            '<span data-serp-warning-field="{}">{} characters</span> — {}'
            "</li>"
        ),
        (
            (
                warning.status.value,
                warning.label,
                warning.field,
                warning.length,
                warning.message,
            )
            for warning in preview.warnings
        ),
    )

    return format_html(
        '<div class="seo-serp-preview" data-seo-serp-preview>'
        '<p class="seo-serp-preview__badge">Google search</p>'
        '<div class="seo-serp-preview__grid">'
        "{}"
        "{}"
        "</div>"
        '<ul class="seo-serp-preview__warnings" data-serp-warnings>{}</ul>'
        '<table class="seo-serp-preview__meta">'
        "<tbody>"
        "<tr><th>URL</th><td><code data-serp-full-url>{}</code></td></tr>"
        "<tr><th>Title (source)</th><td>{}</td></tr>"
        "<tr><th>Description (source)</th><td>{}</td></tr>"
        "</tbody></table>"
        "</div>",
        _serp_result_block(
            variant="desktop",
            label="Desktop",
            title=preview.title_desktop,
            display_url=preview.display_url,
            description=preview.description_desktop,
        ),
        _serp_result_block(
            variant="mobile",
            label="Mobile",
            title=preview.title_mobile,
            display_url=preview.display_url,
            description=preview.description_mobile,
        ),
        warnings_html,
        preview.url or "—",
        preview.sources.get("title", "—"),
        preview.sources.get("description", "—"),
    )


def render_image_seo_html(result: ImageSeoResult) -> str:
    if result.message and not result.checks:
        return render_empty_analysis_html(result.message, analyzer_type="image_seo")

    score_class = score_status_class(result.score)
    images_html = format_html_join(
        "",
        (
            '<tr class="seo-image-seo__row">'
            "<td>{}</td>"
            "<td><code>{}</code></td>"
            "<td>{}</td>"
            "<td>{}</td>"
            "<td>{}</td>"
            "<td>{}</td>"
            "</tr>"
        ),
        (
            (
                row["label"],
                row["filename"],
                row["alt_text"],
                (
                    f'{row["width"]}×{row["height"]} px'
                    if row.get("width") and row.get("height")
                    else "—"
                ),
                (
                    f'{row["file_size_kb"]} KB'
                    if row.get("file_size_kb") is not None
                    else "—"
                ),
                row.get("loading", "—"),
            )
            for row in result.images
        ),
    )
    if not result.images:
        images_html = format_html(
            '<tr><td colspan="6" class="seo-image-seo__empty">No images in content.</td></tr>'
        )

    issues_html = format_html_join(
        "",
        (
            '<li class="seo-image-seo__issue seo-image-seo__issue--{}">'
            "<strong>{}</strong> · {} — {}"
            "</li>"
        ),
        (
            (
                issue.severity,
                issue.label,
                issue.filename,
                issue.issue,
            )
            for issue in result.issues[:10]
        ),
    )
    if not result.issues:
        issues_html = format_html(
            '<li class="seo-image-seo__issue seo-image-seo__issue--good">'
            "No image issues."
            "</li>"
        )

    return format_html(
        '<div class="seo-analyzer seo-image-seo" data-seo-image-seo-analyzer>'
        '<div class="seo-analyzer__header">'
        '<div class="seo-analyzer__score {}" data-seo-score-ring>'
        '<span class="seo-analyzer__score-value" data-seo-score-value>{}</span>'
        '<span class="seo-analyzer__score-label">/100</span>'
        "</div>"
        '<div class="seo-analyzer__meta">'
        "<p><strong>Images analyzed:</strong> "
        '<span data-seo-image-count>{}</span></p>'
        '<p class="seo-analyzer__hint">'
        "Save the post after builder changes to refresh the image analysis."
        "</p></div></div>"
        '<ul class="seo-analyzer__checks" data-seo-checks-list>{}</ul>'
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Images</h4>"
        '<table class="seo-image-seo__table">'
        "<thead><tr>"
        "<th>Location</th><th>File</th><th>Alt</th><th>Dimensions</th><th>Size</th><th>Loading</th>"
        "</tr></thead>"
        '<tbody data-seo-image-list>{}</tbody>'
        "</table></div>"
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Issues found</h4>"
        '<ul class="seo-image-seo__issues" data-seo-image-issues>{}</ul>'
        "</div>"
        '<div class="seo-analyzer__recommendations-wrap">'
        "<h4>Recommendations</h4>"
        '<ul class="seo-analyzer__recommendations" data-seo-recommendations-list>{}</ul>'
        "</div></div>",
        score_class,
        result.score,
        result.image_count,
        _render_checks_html(result.checks),
        images_html,
        issues_html,
        format_html_join(
            "",
            '<li class="seo-analyzer__recommendation">{}</li>',
            ((item,) for item in result.recommendations),
        ),
    )


def render_robots_preview_html(preview: RobotsPreview) -> str:
    directives_html = format_html_join(
        "",
        '<span class="seo-robots-preview__pill">{}</span>',
        ((directive,) for directive in preview.directives),
    )

    return format_html(
        '<div class="seo-robots-preview" data-seo-robots-preview>'
        '<p class="seo-robots-preview__label">Generated robots meta tag:</p>'
        '<code class="seo-robots-preview__tag" data-robots-meta-tag>{}</code>'
        '<div class="seo-robots-preview__directives" data-robots-directives>{}</div>'
        '<p class="seo-analyzer__hint">'
        "Updates live as you change the robots fields above."
        "</p>"
        "</div>",
        preview.meta_tag,
        directives_html,
    )

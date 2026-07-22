"""Admin interfejs za SEO metapodatke."""

from django.contrib import admin
from django.contrib.contenttypes.admin import GenericStackedInline
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from seo.ai_readiness import analyze_ai_readiness
from seo.analysis_ui import (
    render_ai_readiness_html,
    render_cornerstone_analysis_html,
    render_empty_analysis_html,
    render_image_seo_html,
    render_internal_linking_html,
    render_keyword_analysis_html,
    render_open_graph_preview_html,
    render_readability_analysis_html,
    render_robots_preview_html,
    render_schema_preview_html,
    render_serp_preview_html,
    render_slug_analysis_html,
    render_twitter_preview_html,
    render_unified_scoring_html,
)
from seo.image_seo import analyze_image_seo
from seo.robots import build_robots_preview
from seo.serp_preview import build_serp_preview
from seo.unified_scoring import analyze_unified_seo
from seo.cornerstone import analyze_cornerstone_content
from seo.internal_linking import analyze_internal_linking
from seo.keyword_analyzer import analyze_content_object
from seo.open_graph import build_open_graph_tags, validate_og_image_file
from seo.readability_analyzer import analyze_readability_for_object
from seo.reading_time import reading_time_for_content_object
from seo.schema.engine import preview_schema_bundle
from seo.slug_analyzer import analyze_slug_for_object
from seo.twitter_card import build_twitter_card_tags
from seo.models import SeoMetadata
from seo.dashboard_actions import apply_bulk_action
from seo.forms import SeoMetadataAdminForm
from seo.host_adapter import adapt_content_for_seo
from core.locales import SEO_LOCALES
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
from django.core.exceptions import ValidationError


class SeoAnalyzerAdminMixin:
    """Zajednički prikaz i live analiza u adminu."""

    keyword_readonly_field = "keyword_analysis_panel"
    readability_readonly_field = "readability_analysis_panel"
    og_preview_readonly_field = "og_preview_panel"
    reading_time_readonly_field = "reading_time_panel"
    og_image_validation_field = "og_image_validation_panel"
    twitter_preview_readonly_field = "twitter_preview_panel"
    twitter_image_validation_field = "twitter_image_validation_panel"
    schema_preview_readonly_field = "schema_preview_panel"
    internal_linking_readonly_field = "internal_linking_analysis_panel"
    cornerstone_readonly_field = "cornerstone_analysis_panel"
    unified_score_readonly_field = "unified_score_panel"
    serp_preview_readonly_field = "serp_preview_panel"
    robots_preview_readonly_field = "robots_preview_panel"
    slug_analysis_readonly_field = "slug_analysis_panel"
    image_seo_readonly_field = "image_seo_analysis_panel"
    ai_readiness_readonly_field = "ai_readiness_panel"

    class Media:
        css = {
            "all": (
                "admin/css/seo_analyzer.css",
                "admin/css/seo_og_preview.css",
                "admin/css/seo_twitter_preview.css",
                "admin/css/seo_schema_preview.css",
                "admin/css/seo_serp_preview.css",
                "admin/css/seo_drawer.css",
            )
        }
        js = (
            "admin/js/seo_keyword_analyzer.js",
            "admin/js/seo_slug_analyzer.js",
            "admin/js/seo_ai_readiness.js",
            "admin/js/seo_readability_analyzer.js",
            "admin/js/seo_serp_preview.js",
            "admin/js/seo_robots_preview.js",
            "admin/js/seo_image_seo.js",
            "admin/js/seo_og_preview.js",
            "admin/js/seo_twitter_preview.js",
            "admin/js/seo_schema_preview.js",
            "admin/js/seo_internal_linking.js",
            "admin/js/seo_cornerstone.js",
            "admin/js/seo_unified_score.js",
            "admin/js/seo_char_counter.js",
        )

    def _analyzer_config_html(self, *, api_name: str, content_type_id=None, object_id=None):
        return format_html(
            '<div class="seo-analyzer-config" data-seo-analyzer-api="{}" '
            'data-content-type-id="{}" data-object-id="{}" hidden></div>',
            reverse(f"admin:{api_name}"),
            content_type_id or "",
            object_id or "",
        )

    def _resolve_inline_content_object(self, obj):
        if obj is None:
            return None

        content_object = getattr(obj, "content_object", None)
        if content_object is not None and getattr(content_object, "pk", None):
            return adapt_content_for_seo(
                content_object, getattr(obj, "locale", None), obj
            )

        content_type_id = getattr(obj, "content_type_id", None)
        object_id = getattr(obj, "object_id", None)
        if not content_type_id or not object_id:
            return None

        try:
            content_type = ContentType.objects.get(pk=content_type_id)
            model_class = content_type.model_class()
            if model_class is None:
                return None
            raw = model_class.objects.get(pk=object_id)
            return adapt_content_for_seo(raw, getattr(obj, "locale", None), obj)
        except (ContentType.DoesNotExist, ObjectDoesNotExist):
            return None

    def _inline_analyzer_config_ids(self, obj, content_object=None):
        content_object = content_object or self._resolve_inline_content_object(obj)
        content_type_id = getattr(obj, "content_type_id", None) if obj is not None else None
        object_id = getattr(obj, "object_id", None) if obj is not None else None

        if content_object is not None and getattr(content_object, "pk", None):
            if not content_type_id:
                content_type_id = ContentType.objects.get_for_model(content_object).pk
            if not object_id:
                object_id = content_object.pk

        return content_type_id, object_id

    @admin.display(description="Keyword analysis")
    def keyword_analysis_panel(self, obj):
        if obj is None:
            return render_empty_analysis_html(
                "Save the post to see keyword analysis."
            )

        content_object = getattr(obj, "content_object", None)
        if content_object is None or not getattr(content_object, "pk", None):
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Save the post, then enter a focus keyword for live analysis."
                ),
                self._analyzer_config_html(api_name="seo_keyword_analysis"),
            )

        result = analyze_content_object(content_object, obj, visible_only=False)
        return format_html(
            "{}{}",
            render_keyword_analysis_html(result),
            self._analyzer_config_html(
                api_name="seo_keyword_analysis",
                content_type_id=obj.content_type_id,
                object_id=obj.object_id,
            ),
        )

    @admin.display(description="Readability analysis")
    def readability_analysis_panel(self, obj):
        if obj is None:
            return render_empty_analysis_html(
                "Save the post to see readability analysis.",
                analyzer_type="readability",
            )

        content_object = getattr(obj, "content_object", None)
        if content_object is None or not getattr(content_object, "pk", None):
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Save the post to run readability analysis.",
                    analyzer_type="readability",
                ),
                self._analyzer_config_html(api_name="seo_readability_analysis"),
            )

        result = analyze_readability_for_object(content_object, visible_only=False)
        return format_html(
            "{}{}",
            render_readability_analysis_html(result),
            self._analyzer_config_html(
                api_name="seo_readability_analysis",
                content_type_id=obj.content_type_id,
                object_id=obj.object_id,
            ),
        )

    @admin.display(description="OG image validation")
    def og_image_validation_panel(self, obj):
        if obj is None:
            return "—"
        if not obj.og_image:
            return format_html(
                '<p class="seo-og-validation seo-og-validation--neutral">'
                "No custom image — featured image or builder is used."
                "</p>"
            )
        result = validate_og_image_file(obj.og_image)
        messages = format_html_join("", "<li>{}</li>", ((msg,) for msg in result.messages))
        return format_html(
            '<ul class="seo-og-validation seo-og-validation--{}">{}</ul>',
            result.status.value,
            messages,
        )

    @admin.display(description="Open Graph preview")
    def og_preview_panel(self, obj):
        request = getattr(self, "_current_request", None)
        content_object = self._resolve_inline_content_object(obj)
        tags = build_open_graph_tags(
            content_object,
            request,
            metadata=obj,
            visible_only=False,
        )
        content_type_id, object_id = self._inline_analyzer_config_ids(obj, content_object)
        return format_html(
            "{}{}",
            render_open_graph_preview_html(tags),
            self._analyzer_config_html(
                api_name="seo_open_graph_preview",
                content_type_id=content_type_id,
                object_id=object_id,
            ),
        )

    @admin.display(description="Reading time")
    def reading_time_panel(self, obj):
        content_object = self._resolve_inline_content_object(obj)
        if content_object is None:
            return format_html(
                '<p class="seo-analyzer__hint">Estimate will be available once the post has content.</p>'
            )
        minutes = reading_time_for_content_object(content_object)
        return format_html(
            '<p class="seo-analyzer__hint">≈ <strong>{} min</strong> reading time '
            "(based on builder text and intro).</p>",
            minutes,
        )

    @admin.display(description="Twitter image validation")
    def twitter_image_validation_panel(self, obj):
        if obj is None:
            return "—"
        if not obj.twitter_image:
            return format_html(
                '<p class="seo-twitter-validation seo-twitter-validation--neutral">'
                "No custom image — Open Graph or featured image is used."
                "</p>"
            )
        result = validate_og_image_file(obj.twitter_image)
        messages = format_html_join("", "<li>{}</li>", ((msg,) for msg in result.messages))
        return format_html(
            '<ul class="seo-twitter-validation seo-twitter-validation--{}">{}</ul>',
            result.status.value,
            messages,
        )

    @admin.display(description="Twitter Card preview")
    def twitter_preview_panel(self, obj):
        config_html = self._analyzer_config_html(api_name="seo_twitter_card_preview")

        if obj is None:
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Enter Twitter fields — the preview updates as you type.",
                    analyzer_type="twitter",
                ),
                config_html,
            )

        content_object = getattr(obj, "content_object", None)
        if content_object is None or not getattr(content_object, "pk", None):
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Save the post to see the full Twitter preview.",
                    analyzer_type="twitter",
                ),
                config_html,
            )

        og_tags = build_open_graph_tags(content_object, metadata=obj, visible_only=False)
        tags = build_twitter_card_tags(
            content_object,
            metadata=obj,
            og_tags=og_tags,
            visible_only=False,
        )
        return format_html(
            "{}{}",
            render_twitter_preview_html(tags),
            self._analyzer_config_html(
                api_name="seo_twitter_card_preview",
                content_type_id=obj.content_type_id,
                object_id=obj.object_id,
            ),
        )


    @admin.display(description="Schema.org preview")
    def schema_preview_panel(self, obj):
        config_html = self._analyzer_config_html(api_name="seo_schema_preview")

        if obj is None:
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Choose a schema type — the JSON-LD preview updates as you edit.",
                    analyzer_type="schema",
                ),
                config_html,
            )

        content_object = getattr(obj, "content_object", None)
        if content_object is None or not getattr(content_object, "pk", None):
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Save the post to see JSON-LD and Google validation.",
                    analyzer_type="schema",
                ),
                config_html,
            )

        request = getattr(self, "_current_request", None)
        try:
            _, payloads, validation = preview_schema_bundle(
                request,
                content_object,
                metadata=obj,
                schema_type=obj.schema_type or None,
                visible_only=False,
            )
        except Exception as exc:  # noqa: BLE001
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    f"Schema preview unavailable: {exc}",
                    analyzer_type="schema",
                ),
                config_html,
            )
        return format_html(
            "{}{}",
            render_schema_preview_html(
                schema_types=validation.schema_types,
                json_payloads=payloads,
                validation=validation,
            ),
            self._analyzer_config_html(
                api_name="seo_schema_preview",
                content_type_id=obj.content_type_id,
                object_id=obj.object_id,
            ),
        )

    @admin.display(description="Internal links")
    def internal_linking_analysis_panel(self, obj):
        config_html = self._analyzer_config_html(api_name="seo_internal_linking_analysis")

        if obj is None:
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Save the blog post to see internal link suggestions.",
                    analyzer_type="internal_linking",
                ),
                config_html,
            )

        content_object = getattr(obj, "content_object", None)
        if content_object is None or not getattr(content_object, "pk", None):
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Save the post to run the internal link analysis.",
                    analyzer_type="internal_linking",
                ),
                config_html,
            )

        result = analyze_internal_linking(content_object, obj, visible_only=False)
        return format_html(
            "{}{}",
            render_internal_linking_html(result),
            self._analyzer_config_html(
                api_name="seo_internal_linking_analysis",
                content_type_id=obj.content_type_id,
                object_id=obj.object_id,
            ),
        )

    @admin.display(description="Slug analysis")
    def slug_analysis_panel(self, obj):
        config_html = self._analyzer_config_html(api_name="seo_slug_analysis")

        if obj is None:
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Enter a slug in the post details — analysis updates live.",
                    analyzer_type="slug",
                ),
                config_html,
            )

        content_object = getattr(obj, "content_object", None)
        if content_object is None or not getattr(content_object, "pk", None):
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Save the post to see the slug analysis.",
                    analyzer_type="slug",
                ),
                config_html,
            )

        result = analyze_slug_for_object(content_object, obj)
        return format_html(
            "{}{}",
            render_slug_analysis_html(result),
            self._analyzer_config_html(
                api_name="seo_slug_analysis",
                content_type_id=obj.content_type_id,
                object_id=obj.object_id,
            ),
        )

    @admin.display(description="AI readiness")
    def ai_readiness_panel(self, obj):
        config_html = self._analyzer_config_html(api_name="seo_ai_readiness")

        if obj is None:
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Save the post to see the AI readiness analysis.",
                    analyzer_type="ai_readiness",
                ),
                config_html,
            )

        content_object = getattr(obj, "content_object", None)
        if content_object is None or not getattr(content_object, "pk", None):
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Save the post to see the AI readiness analysis.",
                    analyzer_type="ai_readiness",
                ),
                config_html,
            )

        result = analyze_ai_readiness(content_object, obj)
        return format_html(
            "{}{}",
            render_ai_readiness_html(result),
            self._analyzer_config_html(
                api_name="seo_ai_readiness",
                content_type_id=obj.content_type_id,
                object_id=obj.object_id,
            ),
        )

    @admin.display(description="Image analysis")
    def image_seo_analysis_panel(self, obj):
        config_html = self._analyzer_config_html(api_name="seo_image_seo_analysis")

        if obj is None:
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Save the post to see the image analysis.",
                    analyzer_type="image_seo",
                ),
                config_html,
            )

        content_object = getattr(obj, "content_object", None)
        if content_object is None or not getattr(content_object, "pk", None):
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Save the post and add images in the builder.",
                    analyzer_type="image_seo",
                ),
                config_html,
            )

        result = analyze_image_seo(content_object, obj, visible_only=False)
        return format_html(
            "{}{}",
            render_image_seo_html(result),
            self._analyzer_config_html(
                api_name="seo_image_seo_analysis",
                content_type_id=obj.content_type_id,
                object_id=obj.object_id,
            ),
        )

    @admin.display(description="Google SERP preview")
    def serp_preview_panel(self, obj):
        config_html = self._analyzer_config_html(api_name="seo_serp_preview")

        if obj is None:
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Enter SEO title and meta description — the preview updates as you type.",
                    analyzer_type="serp",
                ),
                config_html,
            )

        content_object = getattr(obj, "content_object", None)
        request = getattr(self, "_current_request", None)

        if content_object is None or not getattr(content_object, "pk", None):
            preview = build_serp_preview(None, request, obj)
            return format_html(
                "{}{}",
                render_serp_preview_html(preview),
                config_html,
            )

        preview = build_serp_preview(content_object, request, obj)
        return format_html(
            "{}{}",
            render_serp_preview_html(preview),
            self._analyzer_config_html(
                api_name="seo_serp_preview",
                content_type_id=obj.content_type_id,
                object_id=obj.object_id,
            ),
        )

    @admin.display(description="Robots meta tag")
    def robots_preview_panel(self, obj):
        preview = build_robots_preview(obj if obj and getattr(obj, "pk", None) else None)
        return render_robots_preview_html(preview)

    @admin.display(description="SEO score")
    def unified_score_panel(self, obj):
        config_html = self._analyzer_config_html(api_name="seo_unified_score")

        if obj is None:
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Save the post to see the overall SEO score.",
                    analyzer_type="unified_score",
                ),
                config_html,
            )

        content_object = getattr(obj, "content_object", None)
        if content_object is None or not getattr(content_object, "pk", None):
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Save the post to run unified SEO scoring.",
                    analyzer_type="unified_score",
                ),
                config_html,
            )

        request = getattr(self, "_current_request", None)
        try:
            result = analyze_unified_seo(content_object, obj, request=request, visible_only=False)
        except Exception as exc:  # noqa: BLE001
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    f"SEO score unavailable: {exc}",
                    analyzer_type="unified_score",
                ),
                config_html,
            )
        return format_html(
            "{}{}",
            render_unified_scoring_html(result),
            self._analyzer_config_html(
                api_name="seo_unified_score",
                content_type_id=obj.content_type_id,
                object_id=obj.object_id,
            ),
        )

    @admin.display(description="Cornerstone analysis")
    def cornerstone_analysis_panel(self, obj):
        config_html = self._analyzer_config_html(api_name="seo_cornerstone_analysis")

        if obj is None:
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Save the blog post to see the cornerstone analysis.",
                    analyzer_type="cornerstone",
                ),
                config_html,
            )

        content_object = getattr(obj, "content_object", None)
        if content_object is None or not getattr(content_object, "pk", None):
            return format_html(
                "{}{}",
                render_empty_analysis_html(
                    "Save the post to run the cornerstone analysis.",
                    analyzer_type="cornerstone",
                ),
                config_html,
            )

        result = analyze_cornerstone_content(content_object, obj, visible_only=False)
        return format_html(
            "{}{}",
            render_cornerstone_analysis_html(result),
            self._analyzer_config_html(
                api_name="seo_cornerstone_analysis",
                content_type_id=obj.content_type_id,
                object_id=obj.object_id,
            ),
        )


class SeoScoreListFilter(admin.SimpleListFilter):
    title = "SEO score"
    parameter_name = "seo_score_band"

    def lookups(self, request, model_admin):
        return (
            ("low", "Low (< 40)"),
            ("medium", "Medium (40–69)"),
            ("high", "Good (≥ 70)"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "low":
            return queryset.filter(seo_score__lt=40)
        if value == "medium":
            return queryset.filter(seo_score__gte=40, seo_score__lt=70)
        if value == "high":
            return queryset.filter(seo_score__gte=70)
        return queryset


class MissingSeoTitleFilter(admin.SimpleListFilter):
    title = "SEO title"
    parameter_name = "missing_seo_title"

    def lookups(self, request, model_admin):
        return (("yes", "Missing"),)

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(seo_title="")
        return queryset


class MissingMetaDescriptionFilter(admin.SimpleListFilter):
    title = "Meta description"
    parameter_name = "missing_meta_description"

    def lookups(self, request, model_admin):
        return (("yes", "Missing"),)

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(meta_description="")
        return queryset


@admin.action(description="Recalculate SEO scores")
def recalculate_seo_scores_action(modeladmin, request, queryset):
    apply_bulk_action(
        request,
        "recalculate_scores",
        list(queryset.values_list("pk", flat=True)),
    )


@admin.action(description="Mark as cornerstone")
def mark_cornerstone_action(modeladmin, request, queryset):
    apply_bulk_action(
        request,
        "mark_cornerstone",
        list(queryset.values_list("pk", flat=True)),
    )


@admin.action(description="Remove cornerstone")
def unmark_cornerstone_action(modeladmin, request, queryset):
    apply_bulk_action(
        request,
        "unmark_cornerstone",
        list(queryset.values_list("pk", flat=True)),
    )


@admin.action(description="Set noindex")
def set_noindex_action(modeladmin, request, queryset):
    apply_bulk_action(
        request,
        "set_noindex",
        list(queryset.values_list("pk", flat=True)),
    )


@admin.action(description="Set index")
def set_index_action(modeladmin, request, queryset):
    apply_bulk_action(
        request,
        "set_index",
        list(queryset.values_list("pk", flat=True)),
    )



# Classic fieldsets for hosts without the visual-builder drawer (e.g. exercises).
SEO_EDITOR_FIELDSETS = (
    (
        "Basic SEO",
        {
            "fields": ("locale", "seo_title", "meta_description", "focus_keyword"),
        },
    ),
    (
        "Advanced — URL, robots and structured data",
        {
            "classes": ("collapse",),
            "fields": (
                "canonical_url",
                "secondary_keywords",
                "robots_index",
                "robots_follow",
                "robots_nosnippet",
                "robots_noarchive",
                "robots_max_snippet",
                "robots_max_image_preview",
                "include_in_sitemap",
                "schema_type",
                "breadcrumb_title",
                "is_cornerstone",
            ),
        },
    ),
    (
        "Advanced — Open Graph and Twitter/X",
        {
            "classes": ("collapse",),
            "fields": (
                "og_title",
                "og_description",
                "og_image",
                "og_type",
                "og_url",
                "twitter_title",
                "twitter_description",
                "twitter_image",
                "twitter_card",
            ),
        },
    ),
    (
        "SEO scores",
        {
            "classes": ("collapse",),
            "fields": (
                "seo_score",
                "keyword_score",
                "readability_score",
                "internal_linking_score",
                "image_seo_score",
                "updated_at",
            ),
        },
    ),
)


class SeoMetadataInlineFormSet(BaseGenericInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        locales = {
            form.instance.locale
            for form in self.forms
            if not self._should_delete_form(form)
        }
        if locales != set(SEO_LOCALES):
            raise ValidationError(
                "SEO must have exactly one profile for each language: "
                "Croatian and English."
            )


class SeoMetadataInline(SeoAnalyzerAdminMixin, GenericStackedInline):
    """Yoast-style SEO panel in the visual builder drawer (one profile per locale)."""

    model = SeoMetadata
    form = SeoMetadataAdminForm
    formset = SeoMetadataInlineFormSet
    ct_field = "content_type"
    ct_fk_field = "object_id"
    extra = 0
    max_num = len(SEO_LOCALES)
    can_delete = False
    template = "admin/seo/edit_inline/stacked_no_header.html"
    classes = ("seo-metadata-inline",)
    verbose_name = "SEO profile"
    verbose_name_plural = "SEO profiles"
    readonly_fields = (
        "locale",
        SeoAnalyzerAdminMixin.keyword_readonly_field,
        SeoAnalyzerAdminMixin.slug_analysis_readonly_field,
        SeoAnalyzerAdminMixin.readability_readonly_field,
        SeoAnalyzerAdminMixin.og_image_validation_field,
        SeoAnalyzerAdminMixin.og_preview_readonly_field,
        SeoAnalyzerAdminMixin.reading_time_readonly_field,
        SeoAnalyzerAdminMixin.twitter_image_validation_field,
        SeoAnalyzerAdminMixin.twitter_preview_readonly_field,
        SeoAnalyzerAdminMixin.schema_preview_readonly_field,
        SeoAnalyzerAdminMixin.internal_linking_readonly_field,
        SeoAnalyzerAdminMixin.cornerstone_readonly_field,
        SeoAnalyzerAdminMixin.unified_score_readonly_field,
        SeoAnalyzerAdminMixin.serp_preview_readonly_field,
        SeoAnalyzerAdminMixin.robots_preview_readonly_field,
        SeoAnalyzerAdminMixin.image_seo_readonly_field,
        SeoAnalyzerAdminMixin.ai_readiness_readonly_field,
    )
    fieldsets = (
        (
            "SEO score",
            {
                "fields": (SeoAnalyzerAdminMixin.unified_score_readonly_field,),
                "description": "Overall SEO score (0–100) with categories and recommendations.",
            },
        ),
        (
            "Basic",
            {
                "fields": (
                    "locale",
                    "seo_title",
                    "meta_description",
                    SeoAnalyzerAdminMixin.serp_preview_readonly_field,
                    "focus_keyword",
                    SeoAnalyzerAdminMixin.reading_time_readonly_field,
                    SeoAnalyzerAdminMixin.og_preview_readonly_field,
                ),
                "description": (
                    "Title and meta description drive the Google, Open Graph and Twitter "
                    "previews. Focus keyword is for analysis only."
                ),
            },
        ),
        (
            "Advanced — URL, robots and schema",
            {
                "classes": ("collapse",),
                "fields": (
                    "canonical_url",
                    "secondary_keywords",
                    "robots_index",
                    "robots_follow",
                    "robots_nosnippet",
                    "robots_noarchive",
                    "robots_max_snippet",
                    "robots_max_image_preview",
                    "include_in_sitemap",
                    SeoAnalyzerAdminMixin.robots_preview_readonly_field,
                    "schema_type",
                    "breadcrumb_title",
                    SeoAnalyzerAdminMixin.schema_preview_readonly_field,
                    "is_cornerstone",
                    SeoAnalyzerAdminMixin.cornerstone_readonly_field,
                ),
            },
        ),
        (
            "Advanced — Open Graph and Twitter",
            {
                "classes": ("collapse",),
                "fields": (
                    "og_title",
                    "og_description",
                    "og_image",
                    SeoAnalyzerAdminMixin.og_image_validation_field,
                    "og_type",
                    "og_url",
                    "twitter_title",
                    "twitter_description",
                    "twitter_image",
                    SeoAnalyzerAdminMixin.twitter_image_validation_field,
                    "twitter_card",
                    SeoAnalyzerAdminMixin.twitter_preview_readonly_field,
                ),
            },
        ),
        (
            "Slug analysis",
            {
                "classes": ("collapse",),
                "fields": (SeoAnalyzerAdminMixin.slug_analysis_readonly_field,),
            },
        ),
        (
            "Keyword analysis",
            {
                "classes": ("collapse",),
                "fields": (SeoAnalyzerAdminMixin.keyword_readonly_field,),
                "description": "Green = great · Yellow = OK · Red = needs work",
            },
        ),
        (
            "Readability analysis",
            {
                "classes": ("collapse",),
                "fields": (SeoAnalyzerAdminMixin.readability_readonly_field,),
            },
        ),
        (
            "Image analysis",
            {
                "classes": ("collapse",),
                "fields": (SeoAnalyzerAdminMixin.image_seo_readonly_field,),
            },
        ),
        (
            "AI readiness",
            {
                "classes": ("collapse",),
                "fields": (SeoAnalyzerAdminMixin.ai_readiness_readonly_field,),
            },
        ),
        (
            "Internal links",
            {
                "classes": ("collapse",),
                "fields": (SeoAnalyzerAdminMixin.internal_linking_readonly_field,),
            },
        ),
    )

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).filter(locale__in=SEO_LOCALES)


@admin.register(SeoMetadata)
class SeoMetadataAdmin(SeoAnalyzerAdminMixin, admin.ModelAdmin):
    form = SeoMetadataAdminForm
    actions = (
        recalculate_seo_scores_action,
        mark_cornerstone_action,
        unmark_cornerstone_action,
        set_noindex_action,
        set_index_action,
    )

    def has_module_permission(self, request):
        return False

    list_display = (
        "content_type",
        "object_id",
        "locale",
        "seo_title",
        "seo_score",
        "keyword_score",
        "readability_score",
        "updated_at",
    )
    list_filter = ("locale", "robots_index", "include_in_sitemap", "is_cornerstone")
    search_fields = ("seo_title", "meta_description", "focus_keyword")
    readonly_fields = tuple(
        dict.fromkeys(
            SeoMetadataInline.readonly_fields
            + (
                "content_type",
                "object_id",
                "seo_score",
                "keyword_score",
                "readability_score",
                "internal_linking_score",
                "image_seo_score",
                "updated_at",
            )
        )
    )
    fieldsets = (
        ("Content", {"fields": ("content_type", "object_id")}),
        *SeoMetadataInline.fieldsets,
    )

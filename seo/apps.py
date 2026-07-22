from django.apps import AppConfig


class SeoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "seo"
    verbose_name = "SEO"

    def ready(self):
        from seo import signals  # noqa: F401

        if getattr(self, "_seo_admin_api_ready", False):
            return
        self._seo_admin_api_ready = True

        from django.contrib import admin
        from django.urls import path

        from seo.admin_views import (
            ai_readiness_api,
            cornerstone_analysis_api,
            internal_linking_analysis_api,
            image_seo_analysis_api,
            slug_analysis_api,
            keyword_analysis_api,
            open_graph_preview_api,
            readability_analysis_api,
            schema_preview_api,
            serp_preview_api,
            twitter_card_preview_api,
            unified_score_api,
        )

        original_get_urls = admin.site.get_urls

        def get_urls_with_seo_api():
            custom_urls = [
                path(
                    "seo/slug-analysis/",
                    admin.site.admin_view(slug_analysis_api),
                    name="seo_slug_analysis",
                ),
                path(
                    "seo/keyword-analysis/",
                    admin.site.admin_view(keyword_analysis_api),
                    name="seo_keyword_analysis",
                ),
                path(
                    "seo/readability-analysis/",
                    admin.site.admin_view(readability_analysis_api),
                    name="seo_readability_analysis",
                ),
                path(
                    "seo/open-graph-preview/",
                    admin.site.admin_view(open_graph_preview_api),
                    name="seo_open_graph_preview",
                ),
                path(
                    "seo/twitter-card-preview/",
                    admin.site.admin_view(twitter_card_preview_api),
                    name="seo_twitter_card_preview",
                ),
                path(
                    "seo/schema-preview/",
                    admin.site.admin_view(schema_preview_api),
                    name="seo_schema_preview",
                ),
                path(
                    "seo/internal-linking-analysis/",
                    admin.site.admin_view(internal_linking_analysis_api),
                    name="seo_internal_linking_analysis",
                ),
                path(
                    "seo/cornerstone-analysis/",
                    admin.site.admin_view(cornerstone_analysis_api),
                    name="seo_cornerstone_analysis",
                ),
                path(
                    "seo/unified-score/",
                    admin.site.admin_view(unified_score_api),
                    name="seo_unified_score",
                ),
                path(
                    "seo/serp-preview/",
                    admin.site.admin_view(serp_preview_api),
                    name="seo_serp_preview",
                ),
                path(
                    "seo/image-seo-analysis/",
                    admin.site.admin_view(image_seo_analysis_api),
                    name="seo_image_seo_analysis",
                ),
                path(
                    "seo/ai-readiness/",
                    admin.site.admin_view(ai_readiness_api),
                    name="seo_ai_readiness",
                ),
            ]
            return custom_urls + original_get_urls()

        admin.site.get_urls = get_urls_with_seo_api

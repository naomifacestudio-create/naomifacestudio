"""SEO admin bulk akcije (ModelAdmin action handleri)."""

from __future__ import annotations

from django.contrib import messages

from seo.models import SeoMetadata
from seo.services import refresh_seo_scores


def apply_bulk_action(request, action: str, metadata_ids: list[int]) -> int:
    queryset = SeoMetadata.objects.filter(pk__in=metadata_ids)
    count = queryset.count()
    if not count:
        return 0

    if action == "recalculate_scores":
        updated = 0
        for metadata in queryset.select_related("content_type"):
            refresh_seo_scores(metadata)
            metadata.save(
                update_fields=[
                    "seo_score",
                    "keyword_score",
                    "readability_score",
                    "internal_linking_score",
                    "image_seo_score",
                    "updated_at",
                ]
            )
            updated += 1
        messages.success(request, f"Preračunato SEO ocena: {updated}.")
        return updated

    if action == "mark_cornerstone":
        updated = queryset.update(is_cornerstone=True)
        messages.success(request, f"Označeno kao cornerstone: {updated}.")
        return updated

    if action == "unmark_cornerstone":
        updated = queryset.update(is_cornerstone=False)
        messages.success(request, f"Uklonjena cornerstone oznaka: {updated}.")
        return updated

    if action == "set_noindex":
        updated = queryset.update(robots_index=False, robots_follow=False, include_in_sitemap=False)
        messages.warning(request, f"Postavljeno noindex, nofollow i isključeno iz sitemap-a: {updated}.")
        return updated

    if action == "set_index":
        updated = queryset.update(robots_index=True, robots_follow=True, include_in_sitemap=True)
        messages.success(request, f"Postavljeno index, follow: {updated}.")
        return updated

    if action == "set_nofollow":
        updated = queryset.update(robots_follow=False)
        messages.warning(request, f"Postavljeno nofollow: {updated}.")
        return updated

    if action == "set_follow":
        updated = queryset.update(robots_follow=True)
        messages.success(request, f"Postavljeno follow: {updated}.")
        return updated

    messages.error(request, "Nepoznata bulk akcija.")
    return 0


BULK_ACTIONS = (
    ("", "— Izaberite akciju —"),
    ("recalculate_scores", "Preračunaj SEO ocene"),
    ("mark_cornerstone", "Označi kao cornerstone"),
    ("unmark_cornerstone", "Ukloni cornerstone"),
    ("set_index", "Postavi index"),
    ("set_noindex", "Postavi noindex"),
    ("set_follow", "Postavi follow"),
    ("set_nofollow", "Postavi nofollow"),
)

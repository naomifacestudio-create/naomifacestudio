"""Filtriranje sitemap stavki prema SEO podešavanjima."""

from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Exists, OuterRef, QuerySet

from seo.models import SeoMetadata


def exclude_seo_hidden(queryset: QuerySet, model) -> QuerySet:
    """
    Isključuje objekte čiji SEO zapis ima noindex ili isključen sitemap.

  Objekti bez SeoMetadata zapisa ostaju uključeni.
    """
    content_type = ContentType.objects.get_for_model(model)
    hidden = SeoMetadata.objects.filter(
        content_type=content_type,
        object_id=OuterRef("pk"),
    ).filter(
        models.Q(include_in_sitemap=False) | models.Q(robots_index=False),
    )
    return queryset.annotate(_seo_sitemap_hidden=Exists(hidden)).filter(
        _seo_sitemap_hidden=False,
    )

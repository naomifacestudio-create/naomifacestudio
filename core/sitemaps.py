from django.contrib.contenttypes.models import ContentType
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import translation

from blogs.models import Blog
from education.models import Education
from seo.models import SeoMetadata
from treatments.models import Treatment


def sitemap_content(model):
    content_type = ContentType.objects.get_for_model(model)
    excluded_ids = SeoMetadata.objects.filter(
        content_type=content_type,
        locale="hr",
        include_in_sitemap=False,
    ).values_list("object_id", flat=True)
    return model.objects.filter(is_active=True).exclude(pk__in=excluded_ids)


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "monthly"

    def items(self):
        return (
            "core:home",
            "core:about_me",
            "core:forlled",
            "treatments:list",
            "education:list",
            "blogs:list",
        )

    def location(self, item):
        with translation.override("hr"):
            return reverse(item)


class BuilderContentSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7
    model = None

    def items(self):
        return sitemap_content(self.model)

    def location(self, obj):
        with translation.override("hr"):
            return obj.get_absolute_url("hr")

    def lastmod(self, obj):
        return obj.updated_at


class TreatmentSitemap(BuilderContentSitemap):
    model = Treatment


class EducationSitemap(BuilderContentSitemap):
    model = Education


class BlogSitemap(BuilderContentSitemap):
    model = Blog


sitemaps = {
    "static": StaticViewSitemap,
    "treatments": TreatmentSitemap,
    "education": EducationSitemap,
    "blogs": BlogSitemap,
}

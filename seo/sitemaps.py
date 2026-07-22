from django.contrib.sitemaps import Sitemap
from django.urls import NoReverseMatch, reverse

from blogs.models import BlogPost
from seo.sitemap_filters import exclude_seo_hidden


class StaticViewSitemap(Sitemap):
    """Statične Django stranice."""

    priority = 0.8
    changefreq = "monthly"

    def items(self):
        # Cement used frontend:* names; Reflex uses core/home etc.
        candidates = [
            "home",
            "frontend:home",
            "blog_list",
            "frontend:blog",
            "contact",
            "frontend:kontakt",
        ]
        available = []
        for name in candidates:
            try:
                reverse(name)
                available.append(name)
            except NoReverseMatch:
                continue
        return available or ["home"]

    def location(self, item):
        return reverse(item)


class BlogPostSitemap(Sitemap):
    """Objavljene blog objave."""

    changefreq = "weekly"
    priority = 0.7

    def items(self):
        queryset = (
            BlogPost.objects.publicly_visible()
            .only("slug", "updated_at", "publish_date", "created_at")
            .order_by("-publish_date", "-created_at")
        )
        return exclude_seo_hidden(queryset, BlogPost)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()


class CMSPageSitemap(Sitemap):
    """Aktivne CMS stranice sa javnom rutom (no-op stub on Reflex)."""

    changefreq = "weekly"
    priority = 0.7

    def items(self):
        from core.models import CMSPage

        # Stub CMSPage is not a Django model — nothing to sitemap.
        if not hasattr(CMSPage, "_meta"):
            return []

        pages = (
            CMSPage.objects.filter(is_active=True)
            .only("slug", "page_type", "updated_at")
            .order_by("title")
        )
        try:
            pages = exclude_seo_hidden(pages, CMSPage)
        except Exception:
            return []
        return [page for page in pages if page.get_absolute_url()]

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()


sitemaps = {
    "static": StaticViewSitemap,
    "blog": BlogPostSitemap,
    "cms": CMSPageSitemap,
}

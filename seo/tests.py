from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import reverse

from blogs.models import Blog
from page.schema import empty_page

from .models import SeoMetadata


@override_settings(ALLOWED_HOSTS=["testserver"])
class SeoIntegrationTests(TestCase):
    def setUp(self):
        self.blog = Blog.objects.create(
            title_sr="Srpski naslov",
            slug_sr="srpski-naslov",
            short_description_sr="Srpski opis",
            title_en="English title",
            slug_en="english-title",
            short_description_en="English description",
            body_page_sr=empty_page(),
            body_page_en=empty_page(),
            is_active=False,
        )

    def test_metadata_overrides_content_fallbacks(self):
        SeoMetadata.objects.create(
            content_type=ContentType.objects.get_for_model(self.blog),
            object_id=self.blog.pk,
            locale="sr",
            seo_title="Poseban SEO naslov",
            meta_description="Poseban SEO opis",
            robots_index=False,
        )

        context = self.blog.get_seo_context()
        self.assertEqual(context["title"], "Poseban SEO naslov")
        self.assertEqual(context["description"], "Poseban SEO opis")
        self.assertIn("noindex", context["robots"])
        self.assertIn('"@type": "Article"', context["schema_json"])
        self.assertTrue(context["og_image"])

    def test_admin_preview_is_noindex(self):
        user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        self.client.force_login(user)
        response = self.client.get(
            reverse("blogs:detail", kwargs={"slug": self.blog.slug_sr}),
            {"preview": "1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="robots" content="noindex, nofollow"')

    def test_admin_creates_two_profiles_and_renders_collapsible_seo(self):
        user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        self.client.force_login(user)
        response = self.client.get(
            reverse("admin:blogs_blog_change", args=(self.blog.pk,))
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-builder-drawer-panel="seo"')
        self.assertContains(response, "Srpski i engleski imaju odvojene SEO profile.")
        self.assertEqual(
            set(
                SeoMetadata.objects.filter(object_id=self.blog.pk).values_list(
                    "locale",
                    flat=True,
                )
            ),
            {"sr", "en"},
        )

    def test_deleting_content_deletes_its_seo_profiles(self):
        SeoMetadata.objects.create(
            content_type=ContentType.objects.get_for_model(self.blog),
            object_id=self.blog.pk,
            locale="en",
        )
        self.blog.delete()
        self.assertFalse(SeoMetadata.objects.exists())

    def test_robots_txt_points_to_sitemap(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Sitemap:", response.content)
        self.assertIn(b"/sitemap.xml", response.content)
        self.assertIn(b"Disallow: /admin/", response.content)

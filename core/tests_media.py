from io import BytesIO, StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from blogs.models import Blog
from core.management.commands import cleanup_orphaned_media as orphan_cmd
from core.management.commands.migrate_ckeditor_uploads import (
    destination_path,
    manifest_path,
    rewrite_page,
)
from page.schema import empty_page
from page.structure import create_image_block, create_section


def page_with_image(path, src=""):
    page = empty_page()
    block = create_image_block()
    block["attrs"]["path"] = path
    block["attrs"]["src"] = src or f"/media/{path}"
    block["attrs"]["alt"] = "Alt"
    section = create_section()
    section["rows"][0]["columns"][0]["blocks"] = [block]
    page["sections"] = [section]
    return page


def tiny_png_bytes():
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color=(20, 40, 60)).save(buffer, format="PNG")
    return buffer.getvalue()


@override_settings(ALLOWED_HOSTS=["testserver"])
class OrphanCleanupCommandTests(TestCase):
    @patch.object(orphan_cmd, "iter_storage_files", return_value=("page/images/orphan.webp",))
    @patch.object(orphan_cmd, "referenced_media_paths", return_value=set())
    @patch.object(orphan_cmd.default_storage, "delete")
    def test_orphan_reconciliation_is_dry_run_then_confirmed(
        self, delete, _referenced, _iter
    ):
        output = StringIO()
        call_command("cleanup_orphaned_media", stdout=output)
        self.assertIn("DRY RUN", output.getvalue())
        delete.assert_not_called()

        with patch.object(orphan_cmd, "old_enough_to_delete", return_value=True):
            call_command(
                "cleanup_orphaned_media",
                "--confirm",
                "--minimum-age-hours",
                "0",
                stdout=StringIO(),
            )
        delete.assert_called_once_with("page/images/orphan.webp")

    @override_settings(USE_R2=True)
    def test_remote_cleanup_requires_confirmation(self):
        with self.assertRaises(CommandError):
            call_command("cleanup_orphaned_media", "--confirm", stdout=StringIO())


@override_settings(ALLOWED_HOSTS=["testserver"], MEDIA_URL="/media/")
class MigrateCkeditorUploadsTests(TestCase):
    def test_rewrites_then_deletes_sources_from_manifest(self):
        source = "uploads/2026/07/tretman.webp"
        default_storage.save(source, ContentFile(b"fake-image"))
        page = page_with_image(source, src=f"/media/{source}")
        blog = Blog.objects.create(
            title_sr="Naslov",
            slug_sr="naslov",
            title_en="Title",
            slug_en="title",
            body_page_sr=page,
            body_page_en=page,
            is_active=False,
        )

        call_command("migrate_ckeditor_uploads", "--confirm", stdout=StringIO())
        blog.refresh_from_db()
        target = destination_path(source)
        attrs = blog.body_page_sr["sections"][0]["rows"][0]["columns"][0]["blocks"][0]["attrs"]
        self.assertEqual(attrs["path"], target)
        self.assertTrue(default_storage.exists(target))
        self.assertTrue(default_storage.exists(source))
        self.assertTrue(manifest_path().exists())

        call_command("migrate_ckeditor_uploads", "--delete-sources", stdout=StringIO())
        self.assertFalse(default_storage.exists(source))

    def test_rewrite_page_helper_updates_src_and_path(self):
        page = page_with_image("uploads/a.webp", src="/media/uploads/a.webp")
        rewritten, changed = rewrite_page(
            page,
            {
                "uploads/a.webp": (
                    "page/images/migrated/a.webp",
                    "/media/page/images/migrated/a.webp",
                )
            },
        )
        self.assertTrue(changed)
        attrs = rewritten["sections"][0]["rows"][0]["columns"][0]["blocks"][0]["attrs"]
        self.assertEqual(attrs["path"], "page/images/migrated/a.webp")
        self.assertEqual(attrs["src"], "/media/page/images/migrated/a.webp")


@override_settings(ALLOWED_HOSTS=["testserver"])
class ResolveExistingMediaTests(TestCase):
    def setUp(self):
        self.blog = Blog.objects.create(
            title_sr="Naslov",
            slug_sr="naslov-reuse",
            title_en="Title",
            slug_en="title-reuse",
            body_page_sr=empty_page(),
            body_page_en=empty_page(),
            is_active=False,
        )
        self.path = "page/images/2026/07/shared.png"
        default_storage.save(self.path, ContentFile(tiny_png_bytes()))
        self.user = get_user_model().objects.create_superuser(
            "admin",
            "admin@example.com",
            "password",
        )
        self.client.force_login(self.user)

    def test_resolve_existing_page_image(self):
        url = reverse("admin:blogs_blog_page_resolve_media", args=(self.blog.pk,))
        response = self.client.post(
            url,
            data='{"path": "page/images/2026/07/shared.png"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["path"], self.path)
        self.assertTrue(payload["url"])

    def test_rejects_non_image_page_paths(self):
        video_path = "page/videos/2026/07/clip.mp4"
        default_storage.save(video_path, ContentFile(b"not-an-image"))
        url = reverse("admin:blogs_blog_page_resolve_media", args=(self.blog.pk,))
        response = self.client.post(
            url,
            data='{"path": "page/videos/2026/07/clip.mp4"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "unsupported_path")

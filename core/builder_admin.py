import json
import uuid

from django.contrib import admin
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils import translation
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.content import BUILDER_LOCALES, DEFAULT_LOCALE, LOCALE_SUFFIX
from core.json_media import cleanup_pending_paths
from page.catalog.elements import build_builder_catalog
from page.media import EditorMediaError, EditorMediaService
from page.normalize import normalize_page
from page.schema import empty_page
from page.update import PageVersionConflictError
from page.validation import PageValidationError
from seo.admin import SeoMetadataInline
from seo.services import get_metadata


class LocalizedBuilderAdmin(admin.ModelAdmin):
    change_form_template = "admin/content_builder/change_form.html"
    list_display = ("title_sr", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("title_sr", "title_en", "body_plaintext_sr", "body_plaintext_en")
    readonly_fields = ("created_at", "updated_at")
    inlines = (SeoMetadataInline,)
    fieldsets = (
        (_("Serbian Content"), {
            "fields": ("title_sr", "slug_sr", "short_description_sr"),
        }),
        (_("English Content"), {
            "fields": ("title_en", "slug_en", "short_description_en"),
        }),
        (_("Publishing"), {"fields": ("thumbnail", "is_active")}),
        (_("Dates"), {"fields": ("created_at", "updated_at")}),
    )
    exclude = (
        "body_page_sr", "body_plaintext_sr", "page_version_sr",
        "body_page_en", "body_plaintext_en", "page_version_en",
    )

    class Media:
        css = {"all": ("admin/css/page_builder.css",)}
        js = ("admin/js/page_builder.js", "admin/js/page_builder_submit.js")

    def get_view_on_site_url(self, obj):
        if obj is None:
            return None
        return f"{obj.get_absolute_url()}?preview=1"

    def _locale(self, request):
        value = request.GET.get("locale") or request.POST.get("_builder_locale") or DEFAULT_LOCALE
        return value if value in LOCALE_SUFFIX else DEFAULT_LOCALE

    def add_view(self, request, form_url="", extra_context=None):
        if request.method == "GET":
            create_kwargs = {
                "title_sr": "Bez naslova",
                "slug_sr": f"draft-{uuid.uuid4().hex[:12]}",
                "title_en": "Untitled",
                "slug_en": f"draft-{uuid.uuid4().hex[:12]}",
                "is_active": False,
            }
            # Education requires price; subclasses can override add_view defaults via model
            if hasattr(self.model, "price"):
                create_kwargs["price"] = 0
            obj = self.model.objects.create(**create_kwargs)
            change_url = reverse(
                f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change",
                args=(obj.pk,),
            )
            return HttpResponseRedirect(f"{change_url}?new=1")
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = self.get_object(request, object_id)
        locale = self._locale(request)
        extra_context = dict(extra_context or {})
        if obj:
            if (
                self.has_change_permission(request, obj)
                and request.user.has_perm("seo.add_seometadata")
            ):
                get_metadata(obj, "sr", create=True)
                get_metadata(obj, "en", create=True)
            base = f"admin:{obj._meta.app_label}_{obj._meta.model_name}"
            documents = {}
            for document_locale, suffix in LOCALE_SUFFIX.items():
                page = normalize_page(getattr(obj, f"body_page{suffix}") or empty_page())
                with translation.override(document_locale):
                    preview_url = f"{obj.get_absolute_url()}?preview=1"
                documents[document_locale] = {
                    "locale": document_locale,
                    "page": page,
                    "page_version": getattr(obj, f"page_version{suffix}"),
                    "save_url": reverse(f"{base}_page_save", args=(obj.pk,))
                    + f"?locale={document_locale}",
                    "preview_url": preview_url,
                    "title_field": f"title{suffix}",
                    "slug_field": f"slug{suffix}",
                    "excerpt_field": f"short_description{suffix}",
                    "seo_locale": "en" if document_locale == "en" else "sr",
                }
            current_document = documents[locale]
            extra_context.update({
                "builder_locale": locale,
                "builder_locales": BUILDER_LOCALES,
                "builder_documents": documents,
                "builder_preview_url": current_document["preview_url"],
                "page_builder_initial_page": current_document["page"],
                "page_builder_catalog": build_builder_catalog(),
                "page_builder_version": current_document["page_version"],
                "page_builder_save_url": current_document["save_url"],
                "page_builder_upload_url": reverse(f"{base}_page_upload_image", args=(obj.pk,)),
                "page_builder_video_upload_url": reverse(
                    f"{base}_page_upload_video", args=(obj.pk,)
                ),
                "page_builder_cleanup_pending_url": reverse(
                    f"{base}_page_cleanup", args=(obj.pk,)
                ),
                "page_builder_resolve_media_url": reverse(
                    f"{base}_page_resolve_media", args=(obj.pk,)
                ),
                "builder_changelist_url": reverse(f"{base}_changelist"),
                "builder_seo_enabled": True,
            })
        return super().change_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        for suffix in LOCALE_SUFFIX.values():
            title = getattr(obj, f"title{suffix}", "")
            slug_field = f"slug{suffix}"
            if title and (
                not getattr(obj, slug_field)
                or str(getattr(obj, slug_field)).startswith("draft-")
            ):
                setattr(obj, slug_field, slugify(title) or "content")
        super().save_model(request, obj, form, change)

    def _change_form_redirect(self, request, obj):
        url = reverse(
            f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change",
            args=(obj.pk,),
        )
        return HttpResponseRedirect(f"{url}?locale={self._locale(request)}")

    def response_post_save_add(self, request, obj):
        return self._change_form_redirect(request, obj)

    def response_post_save_change(self, request, obj):
        return self._change_form_redirect(request, obj)

    def get_urls(self):
        urls = super().get_urls()
        info = (self.model._meta.app_label, self.model._meta.model_name)
        custom = [
            path(
                "<int:object_id>/page/save/",
                self.admin_site.admin_view(self.page_save),
                name="%s_%s_page_save" % info,
            ),
            path(
                "<int:object_id>/page/upload-image/",
                self.admin_site.admin_view(self.upload_image),
                name="%s_%s_page_upload_image" % info,
            ),
            path(
                "<int:object_id>/page/upload-video/",
                self.admin_site.admin_view(self.upload_video),
                name="%s_%s_page_upload_video" % info,
            ),
            path(
                "<int:object_id>/page/cleanup/",
                self.admin_site.admin_view(self.cleanup_pending),
                name="%s_%s_page_cleanup" % info,
            ),
            path(
                "<int:object_id>/page/resolve-media/",
                self.admin_site.admin_view(self.resolve_media),
                name="%s_%s_page_resolve_media" % info,
            ),
        ]
        return custom + urls

    def _allowed(self, request, obj):
        return request.user.has_perm(
            f"{obj._meta.app_label}.change_{obj._meta.model_name}"
        )

    def page_save(self, request, object_id):
        obj = get_object_or_404(self.model, pk=object_id)
        if request.method != "POST" or not self._allowed(request, obj):
            return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

        body_page = payload.get("body_page") if isinstance(payload, dict) else None
        if not isinstance(body_page, dict):
            return JsonResponse({"ok": False, "error": "missing_body_page"}, status=400)

        expected = payload.get("expected_page_version")
        if expected is not None:
            try:
                expected = int(expected)
            except (TypeError, ValueError):
                return JsonResponse(
                    {"ok": False, "error": "invalid_expected_version"}, status=400
                )

        locale = request.GET.get("locale", DEFAULT_LOCALE)
        if locale not in LOCALE_SUFFIX:
            return JsonResponse({"ok": False, "error": "unsupported_locale"}, status=400)

        try:
            with transaction.atomic():
                locked = self.model.objects.select_for_update().get(pk=obj.pk)
                result = locked.apply_page(locale, body_page, expected)
        except PageVersionConflictError as exc:
            return JsonResponse(
                {"ok": False, "error": "version_conflict", "page_version": exc.actual},
                status=409,
            )
        except PageValidationError as exc:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "validation_error",
                    "messages": exc.errors,
                    "message": "; ".join(exc.errors),
                },
                status=400,
            )
        except Exception:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "server_error",
                    "message": "Neočekivana greška pri čuvanju stranice.",
                },
                status=500,
            )
        return JsonResponse(
            {"ok": True, "changed": result.changed, "page_version": result.page_version}
        )

    def _upload(self, request, object_id, kind):
        obj = get_object_or_404(self.model, pk=object_id)
        if request.method != "POST" or not self._allowed(request, obj):
            return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
        try:
            service = EditorMediaService()
            result = getattr(service, f"upload_{kind}")(
                request.FILES.get(kind), request=request
            )
        except EditorMediaError as exc:
            return JsonResponse({"ok": False, "error": exc.code}, status=400)
        data = {"ok": True, "path": result.path, "url": result.url}
        if kind == "image":
            data["alt"] = result.alt
        return JsonResponse(data)

    def upload_image(self, request, object_id):
        return self._upload(request, object_id, "image")

    def upload_video(self, request, object_id):
        return self._upload(request, object_id, "video")

    def cleanup_pending(self, request, object_id):
        obj = get_object_or_404(self.model, pk=object_id)
        if request.method != "POST" or not self._allowed(request, obj):
            return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
        try:
            items = json.loads(request.body).get("paths", [])
        except ValueError:
            return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)
        return JsonResponse({"ok": True, "deleted": cleanup_pending_paths(items)})

    def resolve_media(self, request, object_id):
        obj = get_object_or_404(self.model, pk=object_id)
        if request.method != "POST" or not self._allowed(request, obj):
            return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)
        path = str((payload or {}).get("path") or "").strip()
        try:
            result = EditorMediaService().resolve_existing_path(path, request=request)
        except EditorMediaError as exc:
            return JsonResponse({"ok": False, "error": exc.code}, status=400)
        return JsonResponse({"ok": True, "path": result.path, "url": result.url})

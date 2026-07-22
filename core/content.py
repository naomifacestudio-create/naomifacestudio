"""Shared bilingual visual-builder content for Naomi (Croatian + English)."""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone, translation
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from page.schema import page_has_content


# Builder document locales → model field suffixes
LOCALE_SUFFIX = {
    "hr": "_hr",
    "en": "_en",
}

BUILDER_LOCALES = (
    ("hr", "Hrvatski"),
    ("en", "Engleski"),
)

DEFAULT_LOCALE = "hr"


def normalize_builder_locale(locale=None):
    locale = locale or translation.get_language() or DEFAULT_LOCALE
    normalized = str(locale).lower().replace("_", "-")
    if normalized.startswith("en"):
        return "en"
    # Treat leftover Serbian cookies/locales as Croatian after the locale restore.
    if normalized.startswith(("hr", "sr")):
        return "hr"
    return DEFAULT_LOCALE


class BuilderContentQuerySet(models.QuerySet):
    def publicly_visible(self):
        return self.filter(is_active=True, publish_date__lte=timezone.localdate())


class LocalizedBuilderContent(models.Model):
    """Abstract host for the CEGI-style visual page builder (hr + en)."""

    title_hr = models.CharField(_("Title (Croatian)"), max_length=200)
    slug_hr = models.SlugField(_("Slug (Croatian)"), max_length=200, unique=True)
    short_description_hr = models.TextField(_("Short Description (Croatian)"), max_length=500, blank=True)
    body_page_hr = models.JSONField(_("Visual content (Croatian)"), null=True, blank=True)
    body_plaintext_hr = models.TextField(_("Plaintext content (Croatian)"), blank=True, editable=False)
    page_version_hr = models.PositiveIntegerField(_("Content version (Croatian)"), default=0)

    title_en = models.CharField(_("Title (English)"), max_length=200)
    slug_en = models.SlugField(_("Slug (English)"), max_length=200, unique=True)
    short_description_en = models.TextField(_("Short Description (English)"), max_length=500, blank=True)
    body_page_en = models.JSONField(_("Visual content (English)"), null=True, blank=True)
    body_plaintext_en = models.TextField(_("Plaintext content (English)"), blank=True, editable=False)
    page_version_en = models.PositiveIntegerField(_("Content version (English)"), default=0)

    thumbnail = models.ImageField(
        _("Thumbnail Image"),
        upload_to="content/featured/%Y/%m/",
        blank=True,
        help_text=_("Supports WebP format"),
    )
    is_active = models.BooleanField(_("Active"), default=True)
    publish_date = models.DateField(_("Publish date"), default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("-publish_date", "-created_at")


    def _locale(self, locale=None):
        return normalize_builder_locale(locale)

    def localized_field(self, field, locale=None, fallback=True):
        locale = self._locale(locale)
        suffix = LOCALE_SUFFIX[locale]
        value = getattr(self, f"{field}{suffix}")
        if value or not fallback or locale == DEFAULT_LOCALE:
            return value
        return getattr(self, f"{field}{LOCALE_SUFFIX[DEFAULT_LOCALE]}")

    def get_title(self, language_code=None):
        return self.localized_field("title", language_code)

    def get_slug(self, language_code=None):
        return self.localized_field("slug", language_code)

    def get_short_description(self, language_code=None):
        return self.localized_field("short_description", language_code)

    def get_excerpt(self, language_code=None):
        return self.get_short_description(language_code)

    def get_body_page(self, language_code=None):
        return self.localized_field("body_page", language_code, fallback=False)

    def get_body_plaintext(self, language_code=None):
        return self.localized_field("body_plaintext", language_code, fallback=False)

    def get_page_version(self, language_code=None):
        return self.localized_field("page_version", language_code, fallback=False) or 0

    def get_seo_context(self, request=None):
        from seo.services import build_seo_context

        return build_seo_context(self, request)

    def get_meta_title(self):
        return self.get_seo_context()["title"]

    def get_meta_description(self):
        return self.get_seo_context()["description"]

    def has_page_content(self, language_code=None):
        return page_has_content(self.get_body_page(language_code))

    def apply_page(self, locale, page, expected_version=None):
        from page.update import apply_localized_page_update

        return apply_localized_page_update(
            self, locale, page, expected_version=expected_version
        )

    def save(self, *args, **kwargs):
        for locale, suffix in LOCALE_SUFFIX.items():
            title = getattr(self, f"title{suffix}", "") or ""
            slug_field = f"slug{suffix}"
            slug = getattr(self, slug_field, "") or ""
            if title and (not slug or str(slug).startswith("draft-")):
                candidate = slugify(title)[:240] or "content"
                model = type(self)
                unique = candidate
                index = 2
                while model.objects.filter(**{slug_field: unique}).exclude(pk=self.pk).exists():
                    unique = f"{candidate}-{index}"
                    index += 1
                setattr(self, slug_field, unique)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if not self.is_active:
            return
        errors = {}
        title = (self.title_hr or "").strip()
        if not title or title == "Bez naslova":
            errors["title_hr"] = _("Active content must have a real Croatian title.")
        if (self.slug_hr or "").startswith("draft-"):
            errors["slug_hr"] = _("Active content cannot use a temporary draft slug.")
        if not self.has_page_content("hr"):
            errors["is_active"] = _("Active content must have Croatian visual content.")
        if errors:
            raise ValidationError(errors)

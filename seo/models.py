from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.locales import SEO_LOCALES


class SeoMetadata(models.Model):
    LOCALES = (
        ("hr", _("Croatian")),
        ("en", _("English")),
    )
    content_type = models.ForeignKey(
        ContentType, verbose_name=_("content type"), on_delete=models.CASCADE
    )
    object_id = models.PositiveBigIntegerField(_("object ID"))
    content_object = GenericForeignKey()
    locale = models.CharField(_("language"), max_length=12, choices=LOCALES)
    seo_title = models.CharField(_("SEO title"), max_length=200, blank=True)
    meta_description = models.TextField(_("meta description"), max_length=320, blank=True)
    focus_keyword = models.CharField(_("focus keyword"), max_length=120, blank=True)
    secondary_keywords = models.CharField(
        _("secondary keywords"),
        max_length=500,
        blank=True,
        help_text=_("Separate keywords with commas."),
    )
    canonical_url = models.URLField(_("canonical URL"), blank=True)
    robots_index = models.BooleanField(_("allow indexing"), default=True)
    robots_follow = models.BooleanField(_("follow links"), default=True)
    robots_nosnippet = models.BooleanField(_("no snippet in results"), default=False)
    robots_noarchive = models.BooleanField(_("no cached copy"), default=False)
    robots_max_snippet = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("max snippet length"),
        help_text=_("Leave empty to let the search engine use its default length."),
    )
    robots_max_image_preview = models.CharField(
        max_length=12,
        verbose_name=_("image preview in results"),
        choices=(
            ("", _("Default")),
            ("none", _("No image")),
            ("standard", _("Standard")),
            ("large", _("Large")),
        ),
        blank=True,
    )
    include_in_sitemap = models.BooleanField(_("include in sitemap"), default=True)
    og_title = models.CharField(_("Open Graph title"), max_length=200, blank=True)
    og_description = models.TextField(
        _("Open Graph description"), max_length=320, blank=True
    )
    og_image = models.ImageField(
        _("Open Graph image"), upload_to="seo/og/%Y/%m/", blank=True
    )
    og_type = models.CharField(
        _("Open Graph type"), max_length=30, blank=True, default="article"
    )
    og_url = models.URLField(_("Open Graph URL"), blank=True)
    twitter_title = models.CharField(_("Twitter/X title"), max_length=200, blank=True)
    twitter_description = models.TextField(
        _("Twitter/X description"), max_length=320, blank=True
    )
    twitter_image = models.ImageField(
        _("Twitter/X image"), upload_to="seo/twitter/%Y/%m/", blank=True
    )
    twitter_card = models.CharField(
        _("Twitter/X card"), max_length=32, blank=True, default="summary_large_image"
    )
    schema_type = models.CharField(
        _("Schema type"), max_length=40, blank=True, default="Article"
    )
    breadcrumb_title = models.CharField(_("breadcrumb title"), max_length=200, blank=True)
    is_cornerstone = models.BooleanField(_("cornerstone content"), default=False)
    seo_score = models.PositiveSmallIntegerField(_("SEO score"), default=0, editable=False)
    keyword_score = models.PositiveSmallIntegerField(
        _("keyword score"), default=0, editable=False
    )
    readability_score = models.PositiveSmallIntegerField(
        _("readability score"), default=0, editable=False
    )
    internal_linking_score = models.PositiveSmallIntegerField(
        _("internal linking score"), default=0, editable=False
    )
    image_seo_score = models.PositiveSmallIntegerField(
        _("image SEO score"), default=0, editable=False
    )
    updated_at = models.DateTimeField(_("updated"), auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("content_type", "object_id", "locale"),
                name="seo_unique_object_locale",
            ),
            models.CheckConstraint(
                check=models.Q(locale__in=SEO_LOCALES),
                name="seo_locale_hr_or_en",
            ),
        ]
        indexes = [models.Index(fields=("content_type", "object_id", "locale"))]
        verbose_name = _("SEO metadata")
        verbose_name_plural = _("SEO metadata")

    def __str__(self):
        content = self.content_object
        fallback_title = ""
        if content is not None:
            if hasattr(content, "get_title"):
                fallback_title = content.get_title(self.locale)
            else:
                fallback_title = str(content)
        return f"{self.get_locale_display()}: {self.seo_title or fallback_title}"

    def save(self, *args, **kwargs):
        # Scores are refreshed asynchronously in seo.signals after save.
        super().save(*args, **kwargs)

    @property
    def secondary_keywords_list(self) -> list[str]:
        if not self.secondary_keywords.strip():
            return []
        return [
            keyword.strip()
            for keyword in self.secondary_keywords.split(",")
            if keyword.strip()
        ]

    @property
    def robots(self):
        values = [
            "index" if self.robots_index else "noindex",
            "follow" if self.robots_follow else "nofollow",
        ]
        if self.robots_nosnippet:
            values.append("nosnippet")
        if self.robots_noarchive:
            values.append("noarchive")
        if self.robots_max_snippet is not None:
            values.append(f"max-snippet:{self.robots_max_snippet}")
        if self.robots_max_image_preview:
            values.append(f"max-image-preview:{self.robots_max_image_preview}")
        return ", ".join(values)

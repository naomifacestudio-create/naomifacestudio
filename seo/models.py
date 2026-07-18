from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


class SeoMetadata(models.Model):
    LOCALES = (("sr", _("Serbian")), ("en", _("English")))

    content_type = models.ForeignKey(
        ContentType,
        verbose_name=_("content type"),
        on_delete=models.CASCADE,
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
    robots_nosnippet = models.BooleanField(_("disable search snippets"), default=False)
    robots_noarchive = models.BooleanField(_("disable cached copy"), default=False)
    robots_max_snippet = models.IntegerField(
        _("maximum snippet length"),
        null=True,
        blank=True,
        help_text=_("Leave empty to use the search engine default."),
    )
    robots_max_image_preview = models.CharField(
        _("search-result image preview"),
        max_length=12,
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
    og_description = models.TextField(_("Open Graph description"), max_length=320, blank=True)
    og_image = models.ImageField(_("Open Graph image"), upload_to="seo/og/%Y/%m/", blank=True)
    og_type = models.CharField(_("Open Graph type"), max_length=30, blank=True, default="article")
    og_url = models.URLField(_("Open Graph URL"), blank=True)
    twitter_title = models.CharField(_("Twitter/X title"), max_length=200, blank=True)
    twitter_description = models.TextField(_("Twitter/X description"), max_length=320, blank=True)
    twitter_image = models.ImageField(
        _("Twitter/X image"),
        upload_to="seo/twitter/%Y/%m/",
        blank=True,
    )
    twitter_card = models.CharField(
        _("Twitter/X card"),
        max_length=32,
        blank=True,
        default="summary_large_image",
    )
    schema_type = models.CharField(_("Schema type"), max_length=40, blank=True, default="Article")
    breadcrumb_title = models.CharField(_("breadcrumb title"), max_length=200, blank=True)
    is_cornerstone = models.BooleanField(_("cornerstone content"), default=False)
    seo_score = models.PositiveSmallIntegerField(_("SEO score"), default=0, editable=False)
    keyword_score = models.PositiveSmallIntegerField(_("keyword score"), default=0, editable=False)
    readability_score = models.PositiveSmallIntegerField(_("readability score"), default=0, editable=False)
    internal_linking_score = models.PositiveSmallIntegerField(
        _("internal-linking score"),
        default=0,
        editable=False,
    )
    image_seo_score = models.PositiveSmallIntegerField(_("image SEO score"), default=0, editable=False)
    updated_at = models.DateTimeField(_("updated"), auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("content_type", "object_id", "locale"),
                name="seo_unique_object_locale",
            ),
            models.CheckConstraint(
                check=models.Q(locale__in=("sr", "en")),
                name="seo_locale_sr_or_en",
            ),
        ]
        indexes = [models.Index(fields=("content_type", "object_id", "locale"))]
        verbose_name = _("SEO metadata")
        verbose_name_plural = _("SEO metadata")

    def __str__(self):
        return f"{self.get_locale_display()}: {self.seo_title or self.content_object}"

    def save(self, *args, **kwargs):
        keyword = self.focus_keyword.strip().casefold()
        title = self.seo_title.strip()
        description = self.meta_description.strip()
        score = 0
        score += 20 if 30 <= len(title) <= 65 else (10 if title else 0)
        score += 20 if 120 <= len(description) <= 170 else (10 if description else 0)
        if keyword:
            title_keyword = 25 if keyword in title.casefold() else 5
            description_keyword = 20 if keyword in description.casefold() else 5
            score += title_keyword + description_keyword
            self.keyword_score = min(100, (title_keyword + description_keyword) * 2)
        else:
            self.keyword_score = 0
        score += 15 if self.robots_index and self.include_in_sitemap else 0
        self.seo_score = min(score, 100)
        words = description.split()
        self.readability_score = min(100, 50 + len(words) * 2) if words else 0

        content = self.content_object
        if content is not None:
            analysis_locale = "sr-latn" if self.locale == "sr" else "en"
            from page.seo_content import extract_page_analysis_parts

            parts = extract_page_analysis_parts(
                type(
                    "LocalizedContent",
                    (),
                    {
                        "title": content.get_title(analysis_locale),
                        "body_page": content.get_body_page(analysis_locale) or {},
                    },
                )()
            )
            image_count = parts["image_count"]
            self.image_seo_score = (
                100
                if image_count and parts["images_with_alt"] == image_count
                else (
                    0
                    if not image_count
                    else int(parts["images_with_alt"] / image_count * 100)
                )
            )
            self.internal_linking_score = (
                100 if "href=" in str(content.get_body_page(analysis_locale) or {}) else 0
            )
        super().save(*args, **kwargs)

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

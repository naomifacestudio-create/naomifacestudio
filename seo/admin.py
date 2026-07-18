from django.contrib import admin
from django.contrib.contenttypes.admin import GenericStackedInline
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
from django.core.exceptions import ValidationError

from .models import SeoMetadata


SEO_EDITOR_FIELDSETS = (
    (
        "Osnovni SEO",
        {
            "fields": ("locale", "seo_title", "meta_description", "focus_keyword"),
            "description": (
                "Ako SEO naslov ili meta opis ostanu prazni, koristiće se naslov i "
                "kratak opis sadržaja. Glavna ključna reč služi za SEO analizu."
            ),
        },
    ),
    (
        "Napredno — URL, roboti i strukturirani podaci",
        {
            "classes": ("collapse",),
            "fields": (
                "canonical_url",
                "secondary_keywords",
                "robots_index",
                "robots_follow",
                "robots_nosnippet",
                "robots_noarchive",
                "robots_max_snippet",
                "robots_max_image_preview",
                "include_in_sitemap",
                "schema_type",
                "breadcrumb_title",
                "is_cornerstone",
            ),
            "description": (
                "Kanonski URL i Schema.org podaci se automatski formiraju. Menjajte "
                "ova polja samo kada želite da zamenite automatske vrednosti."
            ),
        },
    ),
    (
        "Napredno — Open Graph i Twitter/X",
        {
            "classes": ("collapse",),
            "fields": (
                "og_title",
                "og_description",
                "og_image",
                "og_type",
                "og_url",
                "twitter_title",
                "twitter_description",
                "twitter_image",
                "twitter_card",
            ),
            "description": (
                "Prazna polja koriste SEO naslov, meta opis, naslovnu sliku i "
                "kanonski URL sadržaja."
            ),
        },
    ),
    (
        "SEO ocene",
        {
            "classes": ("collapse",),
            "fields": (
                "seo_score",
                "keyword_score",
                "readability_score",
                "internal_linking_score",
                "image_seo_score",
                "updated_at",
            ),
            "description": "Ocene se automatski preračunavaju pri čuvanju SEO profila.",
        },
    ),
)


class SeoMetadataInlineFormSet(BaseGenericInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        locales = {
            form.instance.locale
            for form in self.forms
            if not self._should_delete_form(form)
        }
        if locales != {"sr", "en"}:
            raise ValidationError("SEO mora imati tačno srpski i engleski profil.")


class SeoMetadataInline(GenericStackedInline):
    model = SeoMetadata
    formset = SeoMetadataInlineFormSet
    ct_field = "content_type"
    ct_fk_field = "object_id"
    extra = 0
    max_num = 2
    can_delete = False
    verbose_name = "SEO profil"
    verbose_name_plural = "SEO profili"
    readonly_fields = (
        "locale",
        "seo_score",
        "keyword_score",
        "readability_score",
        "internal_linking_score",
        "image_seo_score",
        "updated_at",
    )
    fieldsets = SEO_EDITOR_FIELDSETS

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).filter(locale__in=("sr", "en"))


@admin.register(SeoMetadata)
class SeoMetadataAdmin(admin.ModelAdmin):
    list_display = (
        "content_type",
        "object_id",
        "locale",
        "seo_title",
        "seo_score",
        "keyword_score",
        "readability_score",
        "updated_at",
    )
    list_filter = ("locale", "robots_index", "include_in_sitemap", "is_cornerstone")
    search_fields = ("seo_title", "meta_description", "focus_keyword")
    readonly_fields = (
        "content_type",
        "object_id",
        "locale",
        "seo_score",
        "keyword_score",
        "readability_score",
        "internal_linking_score",
        "image_seo_score",
        "updated_at",
    )
    fieldsets = (
        ("Sadržaj", {"fields": ("content_type", "object_id")}),
        *SEO_EDITOR_FIELDSETS,
    )

    def has_module_permission(self, request):
        return False

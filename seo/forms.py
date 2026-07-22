"""SEO admin forme — prijateljski UI iznad robots polja u bazi."""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from seo.models import SeoMetadata

SEARCH_ENGINE_VISIBILITY_CHOICES = (
    (True, _("Show in Google (index, follow)")),
    (False, _("Hide from Google (noindex, nofollow)")),
)


class SeoMetadataAdminForm(forms.ModelForm):
    """Friendlier robots controls for the SEO drawer."""

    class Meta:
        model = SeoMetadata
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "robots_index" in self.fields:
            self.fields["robots_index"].label = _("Search visibility")
            self.fields["robots_index"].widget = forms.RadioSelect(
                choices=SEARCH_ENGINE_VISIBILITY_CHOICES,
            )
            self.fields["robots_index"].help_text = _(
                "Use “Hide from Google” for pages you do not want in search results."
            )
        if "robots_follow" in self.fields:
            self.fields["robots_follow"].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        allow_indexing = cleaned_data.get("robots_index", True)
        cleaned_data["robots_follow"] = allow_indexing
        if not allow_indexing:
            cleaned_data["include_in_sitemap"] = False
        return cleaned_data

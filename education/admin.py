from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin
from import_export import resources

from core.builder_admin import LocalizedBuilderAdmin
from .models import Education


class EducationResource(resources.ModelResource):
    class Meta:
        model = Education
        fields = (
            'id', 'title_sr', 'title_en', 'slug_sr', 'slug_en',
            'short_description_sr', 'short_description_en', 'price', 'is_active',
        )
        export_order = fields


@admin.register(Education)
class EducationAdmin(LocalizedBuilderAdmin, ImportExportModelAdmin):
    resource_class = EducationResource
    list_display = ['title_sr', 'price', 'is_active', 'created_at', 'updated_at']
    search_fields = ['title_sr', 'title_en', 'slug_sr', 'slug_en', 'body_plaintext_sr', 'body_plaintext_en']
    prepopulated_fields = {'slug_sr': ('title_sr',), 'slug_en': ('title_en',)}
    fieldsets = (
        *LocalizedBuilderAdmin.fieldsets[:2],
        (_('Education Details'), {'fields': ('price',)}),
        *LocalizedBuilderAdmin.fieldsets[2:],
    )

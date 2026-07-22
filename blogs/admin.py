from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export import resources

from core.builder_admin import LocalizedBuilderAdmin
from .models import Blog


class BlogResource(resources.ModelResource):
    class Meta:
        model = Blog
        fields = (
            'id', 'title_hr', 'title_en', 'slug_hr', 'slug_en',
            'short_description_hr', 'short_description_en', 'is_active',
        )
        export_order = fields


@admin.register(Blog)
class BlogAdmin(LocalizedBuilderAdmin, ImportExportModelAdmin):
    resource_class = BlogResource
    list_display = ['title_hr', 'publish_date', 'is_active', 'created_at', 'updated_at']
    search_fields = ['title_hr', 'title_en', 'slug_hr', 'slug_en', 'body_plaintext_hr', 'body_plaintext_en']
    prepopulated_fields = {'slug_hr': ('title_hr',), 'slug_en': ('title_en',)}

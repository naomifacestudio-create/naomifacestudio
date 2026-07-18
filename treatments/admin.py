from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export import resources

from core.builder_admin import LocalizedBuilderAdmin
from .models import Treatment


class TreatmentResource(resources.ModelResource):
    class Meta:
        model = Treatment
        fields = ('id', 'title_sr', 'title_en', 'slug_sr', 'slug_en', 'short_description_sr', 
                  'short_description_en', 'price', 'duration_hours', 'duration_minutes', 
                  'pause_hours', 'pause_minutes', 'is_active')
        export_order = ('id', 'title_sr', 'title_en', 'slug_sr', 'slug_en', 'short_description_sr', 
                       'short_description_en', 'price', 'duration_hours', 'duration_minutes', 
                       'pause_hours', 'pause_minutes', 'is_active')


@admin.register(Treatment)
class TreatmentAdmin(LocalizedBuilderAdmin, ImportExportModelAdmin):
    resource_class = TreatmentResource
    list_display = ['title_sr', 'price', 'duration_hours', 'duration_minutes', 'is_active', 'created_at']
    search_fields = [
        'title_sr',
        'title_en',
        'slug_sr',
        'slug_en',
        'body_plaintext_sr',
        'body_plaintext_en',
    ]
    prepopulated_fields = {'slug_sr': ('title_sr',), 'slug_en': ('title_en',)}
    fieldsets = (
        *LocalizedBuilderAdmin.fieldsets[:2],
        (
            'Treatment Details',
            {
                'fields': (
                    'duration_hours',
                    'duration_minutes',
                    'pause_hours',
                    'pause_minutes',
                    'price',
                )
            },
        ),
        *LocalizedBuilderAdmin.fieldsets[2:],
    )

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from .models import Education
from django.conf import settings
import boto3
import logging

logger = logging.getLogger('education')


class EducationResource(resources.ModelResource):
    class Meta:
        model = Education
        fields = ('id', 'title_hr', 'title_en', 'slug_hr', 'slug_en', 'short_description_hr', 
                  'short_description_en', 'price', 'is_active')
        export_order = ('id', 'title_hr', 'title_en', 'slug_hr', 'slug_en', 'short_description_hr', 
                       'short_description_en', 'price', 'is_active')


def delete_media_files_from_r2(file_path):
    """Delete media files from Cloudflare R2"""
    if settings.USE_R2 and file_path:
        try:
            s3_client = boto3.client(
                's3',
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            key = file_path.lstrip('/')
            if settings.AWS_LOCATION:
                key = f"{settings.AWS_LOCATION}/{key}"
            s3_client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
            logger.info(f"Successfully deleted media file from R2: {key}")
        except Exception as e:
            logger.error(f"Error deleting media file from R2: {file_path}. Error: {str(e)}", exc_info=True)


@admin.register(Education)
class EducationAdmin(ImportExportModelAdmin):
    resource_class = EducationResource
    
    fieldsets = (
        (_('Croatian Content'), {
            'fields': ('title_hr', 'slug_hr', 'short_description_hr', 'full_description_hr', 'meta_description_hr')
        }),
        (_('English Content'), {
            'fields': ('title_en', 'slug_en', 'short_description_en', 'full_description_en', 'meta_description_en')
        }),
        (_('Education Details'), {
            'fields': ('price', 'thumbnail', 'is_active')
        }),
    )
    
    list_display = ['title_hr', 'price', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title_hr', 'title_en', 'slug_hr', 'slug_en']
    prepopulated_fields = {'slug_hr': ('title_hr',), 'slug_en': ('title_en',)}
    readonly_fields = ['created_at', 'updated_at']
    
    def save_model(self, request, obj, form, change):
        """Override save to handle file deletion from R2"""
        if change:
            old_obj = Education.objects.get(pk=obj.pk)
            if old_obj.thumbnail and old_obj.thumbnail != obj.thumbnail:
                delete_media_files_from_r2(old_obj.thumbnail.name)
        super().save_model(request, obj, form, change)
    
    def delete_model(self, request, obj):
        """Override delete to remove files from R2"""
        if obj.thumbnail:
            delete_media_files_from_r2(obj.thumbnail.name)
        super().delete_model(request, obj)
    
    def delete_queryset(self, request, queryset):
        """Override bulk delete to remove files from R2"""
        for obj in queryset:
            if obj.thumbnail:
                delete_media_files_from_r2(obj.thumbnail.name)
        super().delete_queryset(request, queryset)


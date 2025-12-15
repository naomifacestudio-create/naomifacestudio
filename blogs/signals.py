from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver
from django.conf import settings
import boto3
import re
import logging
from .models import Blog

logger = logging.getLogger('blogs')


def delete_file_from_r2(file_path):
    """Delete file from Cloudflare R2"""
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
            logger.info(f"Successfully deleted file from R2: {key}")
        except Exception as e:
            logger.error(f"Error deleting file from R2: {file_path}. Error: {str(e)}", exc_info=True)


def extract_image_urls_from_html(html_content):
    """Extract image URLs from HTML content"""
    if not html_content:
        return []
    
    # Find all img src attributes
    pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
    matches = re.findall(pattern, html_content)
    return matches


@receiver(pre_delete, sender=Blog)
def delete_blog_files(sender, instance, **kwargs):
    """Delete blog files from R2 when blog is deleted"""
    if settings.USE_R2:
        # Delete thumbnail
        if instance.thumbnail:
            delete_file_from_r2(instance.thumbnail.name)
        
        # Delete images from descriptions
        for field in ['full_description_hr', 'full_description_en']:
            content = getattr(instance, field, '')
            if content:
                image_urls = extract_image_urls_from_html(content)
                for url in image_urls:
                    # Extract path from URL
                    if '/media/' in url:
                        path = url.split('/media/')[1]
                        delete_file_from_r2(path)


@receiver(pre_save, sender=Blog)
def cleanup_old_blog_files(sender, instance, **kwargs):
    """Delete old files when blog is updated"""
    if settings.USE_R2 and instance.pk:
        try:
            old_instance = Blog.objects.get(pk=instance.pk)
            
            # Delete old thumbnail if changed
            if old_instance.thumbnail and old_instance.thumbnail != instance.thumbnail:
                delete_file_from_r2(old_instance.thumbnail.name)
            
            # Compare descriptions and delete removed images
            for field in ['full_description_hr', 'full_description_en']:
                old_content = getattr(old_instance, field, '')
                new_content = getattr(instance, field, '')
                
                if old_content and new_content:
                    old_images = set(extract_image_urls_from_html(old_content))
                    new_images = set(extract_image_urls_from_html(new_content))
                    removed_images = old_images - new_images
                    
                    for url in removed_images:
                        if '/media/' in url:
                            path = url.split('/media/')[1]
                            delete_file_from_r2(path)
        except Blog.DoesNotExist:
            pass


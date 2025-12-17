from django.db.models.signals import pre_delete, pre_save, post_save
from django.dispatch import receiver
from django.conf import settings
import boto3
import re
import logging
from .models import Education

logger = logging.getLogger('education')


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


def extract_file_path_from_url(url):
    """Extract file path from image URL (handles both custom domain and regular URLs)"""
    if not url:
        return None
    
    # Extract path after /media/
    if '/media/' in url:
        path = url.split('/media/')[1]
        # Remove query parameters if any
        if '?' in path:
            path = path.split('?')[0]
        return path
    
    return None


def get_all_used_image_paths():
    """Get all image file paths that are currently used in blogs, treatments, and education"""
    used_paths = set()
    
    # Import here to avoid circular imports
    from blogs.models import Blog
    from treatments.models import Treatment
    from education.models import Education
    
    # Get images from all blogs
    for blog in Blog.objects.all():
        for field in ['full_description_hr', 'full_description_en']:
            content = getattr(blog, field, '')
            if content:
                image_urls = extract_image_urls_from_html(content)
                for url in image_urls:
                    path = extract_file_path_from_url(url)
                    if path:
                        used_paths.add(path)
    
    # Get images from all treatments
    for treatment in Treatment.objects.all():
        for field in ['full_description_hr', 'full_description_en']:
            content = getattr(treatment, field, '')
            if content:
                image_urls = extract_image_urls_from_html(content)
                for url in image_urls:
                    path = extract_file_path_from_url(url)
                    if path:
                        used_paths.add(path)
    
    # Get images from all education items
    for education in Education.objects.all():
        for field in ['full_description_hr', 'full_description_en']:
            content = getattr(education, field, '')
            if content:
                image_urls = extract_image_urls_from_html(content)
                for url in image_urls:
                    path = extract_file_path_from_url(url)
                    if path:
                        used_paths.add(path)
    
    return used_paths


def cleanup_orphaned_ckeditor_uploads():
    """Clean up orphaned images from CKEditor uploads folder that are not used in any blog, treatment, or education"""
    if not settings.USE_R2:
        return
    
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        
        # Get upload path from settings
        upload_path = settings.CKEDITOR_UPLOAD_PATH.rstrip('/')
        location = settings.AWS_LOCATION
        prefix = f"{location}/{upload_path}/" if location else f"{upload_path}/"
        
        # List all files in uploads folder
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Prefix=prefix)
        
        all_upload_files = []
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    # Get relative path (remove location prefix)
                    if location and key.startswith(f"{location}/"):
                        relative_path = key[len(f"{location}/"):]
                    else:
                        relative_path = key
                    all_upload_files.append(relative_path)
        
        # Get all used image paths
        used_paths = get_all_used_image_paths()
        
        # Find orphaned files (in uploads but not used)
        orphaned_files = []
        for upload_file in all_upload_files:
            # Only check files in uploads folder
            if upload_file.startswith(upload_path + '/'):
                if upload_file not in used_paths:
                    orphaned_files.append(upload_file)
        
        # Delete orphaned files
        deleted_count = 0
        for file_path in orphaned_files:
            delete_file_from_r2(file_path)
            deleted_count += 1
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} orphaned CKEditor upload files from R2")
        
    except Exception as e:
        logger.error(f"Error cleaning up orphaned CKEditor uploads: {str(e)}", exc_info=True)


@receiver(pre_delete, sender=Education)
def delete_education_files(sender, instance, **kwargs):
    """Delete education files from R2 when education is deleted"""
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


@receiver(pre_save, sender=Education)
def cleanup_old_education_files(sender, instance, **kwargs):
    """Delete old files when education is updated"""
    if settings.USE_R2 and instance.pk:
        try:
            old_instance = Education.objects.get(pk=instance.pk)
            
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
        except Education.DoesNotExist:
            pass


@receiver(post_save, sender=Education)
def cleanup_orphaned_uploads_on_save(sender, instance, **kwargs):
    """Clean up orphaned CKEditor uploads after education is saved"""
    # Clean up orphaned uploads that are not used in any blog, treatment, or education
    cleanup_orphaned_ckeditor_uploads()



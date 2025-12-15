"""
Custom storage backend for Cloudflare R2 with custom domain support.
"""
from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class R2Storage(S3Boto3Storage):
    """
    Custom S3 storage backend for Cloudflare R2 with explicit custom domain support.
    """
    location = 'media'
    default_acl = 'public-read'
    file_overwrite = False
    
    def url(self, name):
        """
        Generate URL for the file. Uses custom domain if configured.
        The parent class handles location prefix, so we just need to ensure
        custom domain is used when set.
        """
        # Check if custom domain is set (it can be None or a string)
        custom_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)
        
        if custom_domain and custom_domain.strip():
            # Build URL with custom domain
            # The name parameter is the file path relative to location
            # We need to add location prefix: https://custom-domain/location/name
            custom_domain_clean = custom_domain.strip().rstrip('/')
            if not custom_domain_clean.startswith('http'):
                custom_domain_clean = f'https://{custom_domain_clean}'
            
            # Construct full path: location/name
            file_path = f'{self.location}/{name}'.replace('//', '/').lstrip('/')
            url = f'{custom_domain_clean}/{file_path}'
            return url
        
        # Fall back to parent implementation (uses endpoint URL)
        return super().url(name)


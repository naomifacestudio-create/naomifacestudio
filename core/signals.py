from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import EmailCollection, UserProfile


@receiver(post_save, sender=User)
def collect_user_email(sender, instance, created, **kwargs):
    """Collect email when user is created with user details"""
    if created and instance.email:
        # Get profile if it exists
        profile = None
        try:
            profile = instance.profile
        except UserProfile.DoesNotExist:
            pass
        
        # Collect email with user details (update if exists, as this has the most complete info)
        EmailCollection.collect_email(
            email=instance.email,
            source='User Registration',
            first_name=instance.first_name or (profile.first_name if profile else ''),
            last_name=instance.last_name or (profile.last_name if profile else ''),
            mobile=profile.mobile if profile else '',
            user=instance,
            update_user_info=True,  # Update if email already exists from contact form
        )


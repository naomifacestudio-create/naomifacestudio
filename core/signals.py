from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import EmailCollection


@receiver(post_save, sender=User)
def collect_user_email(sender, instance, created, **kwargs):
    """Collect email when user is created"""
    if created and instance.email:
        EmailCollection.objects.get_or_create(
            email=instance.email,
            defaults={
                'source': 'User Registration',
                'user': instance
            }
        )


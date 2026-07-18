from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from core.json_media import cleanup_deleted_page_media
from core.media_refs import delete_later_if_unreferenced, file_name

from .models import Treatment


@receiver(pre_save, sender=Treatment)
def capture_old_treatment_thumbnail(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_thumbnail_name = ""
        return
    old = Treatment.objects.filter(pk=instance.pk).only("thumbnail").first()
    instance._old_thumbnail_name = file_name(old, "thumbnail") if old else ""


@receiver(post_save, sender=Treatment)
def cleanup_replaced_treatment_thumbnail(sender, instance, **kwargs):
    old = getattr(instance, "_old_thumbnail_name", "")
    if old and old != file_name(instance, "thumbnail"):
        delete_later_if_unreferenced(old)


@receiver(post_delete, sender=Treatment)
def delete_treatment_media(sender, instance, **kwargs):
    cleanup_deleted_page_media(instance)
    delete_later_if_unreferenced(file_name(instance, "thumbnail"))

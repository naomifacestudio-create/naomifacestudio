"""SEO signal handlers — score refresh + media cleanup."""

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from blogs.models import Blog
from core.media_refs import delete_later_if_unreferenced, file_name
from education.models import Education
from treatments.models import Treatment

from seo.models import SeoMetadata
from seo.services import refresh_seo_scores


@receiver(pre_save, sender=SeoMetadata)
def seo_metadata_pre_save(sender, instance: SeoMetadata, **kwargs):
    refresh_seo_scores(instance)


@receiver(post_delete, sender=Blog)
@receiver(post_delete, sender=Education)
@receiver(post_delete, sender=Treatment)
def delete_content_seo_profiles(sender, instance, **kwargs):
    content_type = ContentType.objects.get_for_model(sender)
    SeoMetadata.objects.filter(
        content_type=content_type,
        object_id=instance.pk,
    ).delete()


@receiver(pre_save, sender=SeoMetadata)
def capture_old_seo_media(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_og_image_name = ""
        instance._old_twitter_image_name = ""
        return
    old = sender.objects.filter(pk=instance.pk).only("og_image", "twitter_image").first()
    instance._old_og_image_name = file_name(old, "og_image") if old else ""
    instance._old_twitter_image_name = file_name(old, "twitter_image") if old else ""


@receiver(post_save, sender=SeoMetadata)
def cleanup_replaced_seo_media(sender, instance, **kwargs):
    old_og = getattr(instance, "_old_og_image_name", "")
    old_twitter = getattr(instance, "_old_twitter_image_name", "")
    if old_og and old_og != file_name(instance, "og_image"):
        delete_later_if_unreferenced(old_og)
    if old_twitter and old_twitter != file_name(instance, "twitter_image"):
        delete_later_if_unreferenced(old_twitter)


@receiver(post_delete, sender=SeoMetadata)
def cleanup_deleted_seo_media(sender, instance, **kwargs):
    delete_later_if_unreferenced(file_name(instance, "og_image"))
    delete_later_if_unreferenced(file_name(instance, "twitter_image"))

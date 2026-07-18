"""Shared reference checks for media cleanup across builder, SEO, and FileFields."""

from django.apps import apps
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import FileField

from core.json_media import all_page_media_refs


def file_is_referenced(path):
    if not path:
        return False
    if any(ref.path == path for ref in all_page_media_refs()):
        return True
    for model in apps.get_models():
        for field in model._meta.fields:
            if not isinstance(field, FileField):
                continue
            if model._default_manager.filter(**{field.attname: path}).exists():
                return True
    return False


def delete_later_if_unreferenced(path):
    if not path:
        return

    def cleanup():
        if not file_is_referenced(path):
            default_storage.delete(path)

    transaction.on_commit(cleanup)


def file_name(instance, field):
    value = getattr(instance, field, None)
    return value.name if value else ""


def referenced_media_paths():
    referenced = {ref.path for ref in all_page_media_refs() if ref.storage == "default"}
    for model in apps.get_models():
        fields = [field for field in model._meta.fields if isinstance(field, FileField)]
        if not fields:
            continue
        for values in model._default_manager.values_list(
            *(field.attname for field in fields)
        ):
            referenced.update(value for value in values if value)
    return referenced

"""Helpers shared by destructive media maintenance commands."""

import os

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import CommandError


def uses_remote_media_storage():
    if getattr(settings, "USE_R2", False):
        return True
    storage_class = f"{default_storage.__class__.__module__}.{default_storage.__class__.__name__}"
    return "s3" in storage_class.lower() or "r2" in storage_class.lower()


def require_destructive_confirmation(
    *,
    confirm: bool,
    production_confirmation: str,
    env_var: str,
    expected_token: str,
    action_label: str,
):
    if not confirm:
        return
    if not uses_remote_media_storage():
        return
    if os.environ.get(env_var) != "1" or production_confirmation != expected_token:
        raise CommandError(
            f"{action_label} against remote media storage requires {env_var}=1 and "
            f"--production-confirmation={expected_token}."
        )

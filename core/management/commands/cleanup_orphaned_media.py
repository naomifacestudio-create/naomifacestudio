import os
from pathlib import Path, PurePosixPath

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.management_safety import require_destructive_confirmation
from core.media_refs import referenced_media_paths


MANAGED_PREFIXES = (
    "page",
    "content/featured",
    "seo/og",
    "seo/twitter",
    "blogs/thumbnails",
    "education/thumbnails",
    "treatments/thumbnails",
)


def iter_storage_files(prefix):
    try:
        directories, files = default_storage.listdir(prefix)
    except (FileNotFoundError, OSError):
        return
    for filename in files:
        yield str(PurePosixPath(prefix, filename))
    for directory in directories:
        yield from iter_storage_files(str(PurePosixPath(prefix, directory)))


def old_enough_to_delete(path, minimum_age_hours):
    if minimum_age_hours <= 0:
        return True
    try:
        modified = default_storage.get_modified_time(path)
    except (NotImplementedError, OSError):
        return False
    if timezone.is_naive(modified):
        modified = timezone.make_aware(modified, timezone.get_current_timezone())
    age = timezone.now() - modified
    return age.total_seconds() >= minimum_age_hours * 3600


class Command(BaseCommand):
    help = (
        "Audit managed media prefixes and delete unreferenced orphans only with "
        "--confirm. Defaults to dry-run."
    )

    def add_arguments(self, parser):
        parser.add_argument("--confirm", action="store_true")
        parser.add_argument(
            "--minimum-age-hours",
            type=int,
            default=24,
            help="Protect recent pending uploads; defaults to 24 hours.",
        )
        parser.add_argument(
            "--production-confirmation",
            default="",
            help="Required for remote media storage: DELETE-ORPHANED-MEDIA.",
        )

    def handle(self, *args, **options):
        require_destructive_confirmation(
            confirm=options["confirm"],
            production_confirmation=options["production_confirmation"],
            env_var="R2_ORPHAN_CLEANUP_CONFIRMED",
            expected_token="DELETE-ORPHANED-MEDIA",
            action_label="Orphan cleanup",
        )

        minimum_age_hours = max(0, options["minimum_age_hours"])
        referenced = referenced_media_paths()
        stored = {
            path for prefix in MANAGED_PREFIXES for path in iter_storage_files(prefix)
        }
        orphaned = sorted(stored - referenced)
        deletable = [
            path for path in orphaned if old_enough_to_delete(path, minimum_age_hours)
        ]
        self.stdout.write(
            f"Managed files={len(stored)}, referenced={len(stored & referenced)}, "
            f"orphaned={len(orphaned)}, eligible_after_{minimum_age_hours}h={len(deletable)}."
        )
        for path in orphaned:
            self.stdout.write(f"ORPHAN {path}")

        if not options["confirm"]:
            self.stdout.write(self.style.WARNING("DRY RUN only."))
            return

        for path in deletable:
            default_storage.delete(path)
        self.stdout.write(self.style.SUCCESS(f"Deleted {len(deletable)} orphaned files."))

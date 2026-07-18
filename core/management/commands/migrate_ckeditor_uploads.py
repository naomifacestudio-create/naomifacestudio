"""Copy legacy CKEditor uploads/ objects into page/images/ and rewrite builder JSON."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.json_media import PAGE_BODY_FIELDS, builder_models, extract_media_refs_from_page
from core.management_safety import require_destructive_confirmation
from core.media_refs import file_is_referenced


def destination_path(source_path: str) -> str:
    relative = (
        source_path[len("uploads/") :]
        if source_path.startswith("uploads/")
        else source_path
    )
    return str(PurePosixPath("page/images/migrated") / relative)


def rewrite_page(page, mapping: dict[str, tuple[str, str]]):
    """Rewrite image/video paths and srcs. mapping: old_path -> (new_path, new_url)."""
    if not isinstance(page, dict) or not mapping:
        return page, False
    changed = False
    for section in page.get("sections") or []:
        for row in section.get("rows") or []:
            for column in row.get("columns") or []:
                for block in column.get("blocks") or []:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") not in {"image", "video"}:
                        continue
                    attrs = block.get("attrs")
                    if not isinstance(attrs, dict):
                        continue
                    for key in ("path", "poster_path"):
                        old = str(attrs.get(key) or "").strip()
                        if old in mapping:
                            attrs[key] = mapping[old][0]
                            changed = True
                    for key in ("src", "poster", "poster_src"):
                        old_value = str(attrs.get(key) or "").strip()
                        if not old_value:
                            continue
                        for old_path, (new_path, new_url) in mapping.items():
                            if old_path in old_value or old_value.endswith(old_path):
                                attrs[key] = new_url
                                if key == "src" and not str(attrs.get("path") or "").strip():
                                    attrs["path"] = new_path
                                if key in {"poster", "poster_src"} and not str(
                                    attrs.get("poster_path") or ""
                                ).strip():
                                    attrs["poster_path"] = new_path
                                changed = True
                                break
    return page, changed


def collect_upload_paths():
    paths = set()
    for model in builder_models():
        for pages in model.objects.values_list(*PAGE_BODY_FIELDS):
            for page in pages:
                for ref in extract_media_refs_from_page(page):
                    if ref.path.startswith("uploads/"):
                        paths.add(ref.path)
    return sorted(paths)


def copy_upload(source_path: str) -> tuple[str, str]:
    target = destination_path(source_path)
    if default_storage.exists(target):
        return target, default_storage.url(target)
    if not default_storage.exists(source_path):
        raise FileNotFoundError(source_path)
    with default_storage.open(source_path, "rb") as handle:
        saved = default_storage.save(target, File(handle, name=Path(source_path).name))
    return saved, default_storage.url(saved)


def manifest_path() -> Path:
    directory = Path(settings.BASE_DIR) / "var"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "ckeditor_uploads_migration.json"


def write_manifest(mapping: dict[str, tuple[str, str]]):
    payload = {
        "created_at": timezone.now().isoformat(),
        "sources": [
            {"source": source, "target": target, "url": url}
            for source, (target, url) in sorted(mapping.items())
        ],
    }
    manifest_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_manifest_sources() -> list[str]:
    path = manifest_path()
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [item["source"] for item in payload.get("sources") or [] if item.get("source")]


class Command(BaseCommand):
    help = (
        "Copy CKEditor uploads/ media into page/images/migrated/ and rewrite visual "
        "builder JSON references. Dry-run by default; use --confirm to apply. "
        "Use --delete-sources after verification to remove sources listed in the "
        "local migration manifest."
    )

    def add_arguments(self, parser):
        parser.add_argument("--confirm", action="store_true")
        parser.add_argument(
            "--delete-sources",
            action="store_true",
            help=(
                "Delete uploads/ sources from the migration manifest after a global "
                "reference check. Can be used alone after a successful --confirm run."
            ),
        )
        parser.add_argument(
            "--production-confirmation",
            default="",
            help="Required for remote media storage: MIGRATE-CKEDITOR-UPLOADS.",
        )

    def handle(self, *args, **options):
        destructive = options["confirm"] or options["delete_sources"]
        require_destructive_confirmation(
            confirm=destructive,
            production_confirmation=options["production_confirmation"],
            env_var="R2_UPLOADS_MIGRATION_CONFIRMED",
            expected_token="MIGRATE-CKEDITOR-UPLOADS",
            action_label="CKEditor uploads migration",
        )

        if options["confirm"]:
            self._migrate(options)
        elif options["delete_sources"]:
            self._delete_sources_from_manifest()
        else:
            upload_paths = collect_upload_paths()
            self.stdout.write(f"Found {len(upload_paths)} unique uploads/ references.")
            for path in upload_paths:
                self.stdout.write(f"MAP {path} -> {destination_path(path)}")
            self.stdout.write(self.style.WARNING("DRY RUN only."))

    def _migrate(self, options):
        upload_paths = collect_upload_paths()
        self.stdout.write(f"Found {len(upload_paths)} unique uploads/ references.")
        if not upload_paths:
            self.stdout.write(self.style.SUCCESS("Nothing to migrate."))
            if options["delete_sources"]:
                self._delete_sources_from_manifest()
            return

        mapping = {}
        missing = []
        for path in upload_paths:
            target = destination_path(path)
            self.stdout.write(f"MAP {path} -> {target}")
            try:
                mapping[path] = copy_upload(path)
            except FileNotFoundError:
                missing.append(path)
                self.stdout.write(self.style.ERROR(f"MISSING {path}"))

        if missing:
            raise CommandError(
                f"Aborting rewrite because {len(missing)} source file(s) are missing."
            )

        rewritten = 0
        with transaction.atomic():
            for model in builder_models():
                for obj in model.objects.all().iterator():
                    updates = {}
                    for field in PAGE_BODY_FIELDS:
                        page = getattr(obj, field, None)
                        new_page, changed = rewrite_page(page, mapping)
                        if changed:
                            updates[field] = new_page
                    if updates:
                        model.objects.filter(pk=obj.pk).update(**updates)
                        rewritten += 1

        write_manifest(mapping)
        self.stdout.write(self.style.SUCCESS(f"Rewrote {rewritten} content object(s)."))
        self.stdout.write(f"Wrote migration manifest: {manifest_path()}")

        if options["delete_sources"]:
            self._delete_sources_from_manifest()
        else:
            self.stdout.write(
                "Source uploads/ files were kept. After verify, run: "
                "python manage.py migrate_ckeditor_uploads --delete-sources"
            )

    def _delete_sources_from_manifest(self):
        sources = read_manifest_sources()
        if not sources:
            raise CommandError(
                "No migration manifest found. Run --confirm first, or pass "
                "--confirm --delete-sources in one step."
            )
        deleted = 0
        skipped = 0
        for path in sources:
            if file_is_referenced(path):
                skipped += 1
                self.stdout.write(self.style.WARNING(f"SKIP still-referenced {path}"))
                continue
            if default_storage.exists(path):
                default_storage.delete(path)
                deleted += 1
                self.stdout.write(f"DELETED {path}")
            else:
                self.stdout.write(f"ALREADY_GONE {path}")
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted} source uploads/ file(s); skipped {skipped}."
            )
        )

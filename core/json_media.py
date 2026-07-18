"""Reference tracking and conservative cleanup for page-builder media."""
from dataclasses import dataclass

from django.core.files.storage import default_storage
from django.db import transaction


@dataclass(frozen=True)
class JsonMediaRef:
    storage: str
    path: str


PAGE_BODY_FIELDS = ("body_page_sr", "body_page_en")
CLEANUP_PREFIXES = ("page/",)


def extract_media_refs_from_page(page):
    refs = set()
    if not isinstance(page, dict):
        return refs
    for section in page.get("sections") or []:
        for row in section.get("rows") or []:
            for column in row.get("columns") or []:
                for block in column.get("blocks") or []:
                    if not isinstance(block, dict):
                        continue
                    block_type = block.get("type")
                    if block_type not in {"image", "video"}:
                        continue
                    attrs = block.get("attrs") or {}
                    if not isinstance(attrs, dict):
                        continue
                    path = str(attrs.get("path") or "").strip()
                    if path:
                        refs.add(JsonMediaRef("default", path))
                    if block_type == "video":
                        poster_path = str(attrs.get("poster_path") or "").strip()
                        poster_src = str(
                            attrs.get("poster") or attrs.get("poster_src") or ""
                        ).strip()
                        if poster_path:
                            refs.add(JsonMediaRef("default", poster_path))
                        elif poster_src and not poster_src.startswith(
                            ("http://", "https://", "/")
                        ):
                            refs.add(JsonMediaRef("default", poster_src))
    return refs


def builder_models():
    models = []
    try:
        from blogs.models import Blog

        models.append(Blog)
    except Exception:
        pass
    try:
        from education.models import Education

        models.append(Education)
    except Exception:
        pass
    try:
        from treatments.models import Treatment

        models.append(Treatment)
    except Exception:
        pass
    return models


def all_page_media_refs():
    refs = set()
    for model in builder_models():
        for pages in model.objects.values_list(*PAGE_BODY_FIELDS):
            for page in pages:
                refs.update(extract_media_refs_from_page(page))
    return refs


def _is_managed_path(path):
    return any(path.startswith(prefix) for prefix in CLEANUP_PREFIXES)


def _delete_if_unreferenced(path):
    from core.media_refs import file_is_referenced

    if _is_managed_path(path) and not file_is_referenced(path):
        default_storage.delete(path)


def cleanup_removed_json_media(old_refs, new_refs):
    """Delete only removed builder files that nothing still references."""
    removed = set(old_refs) - set(new_refs)
    if not removed:
        return 0
    deleted = 0
    for ref in removed:
        if ref.storage == "default" and _is_managed_path(ref.path):
            transaction.on_commit(lambda path=ref.path: _delete_if_unreferenced(path))
            deleted += 1
    return deleted


def cleanup_deleted_page_media(instance):
    """Delete page media from a removed object unless anything still uses it."""
    refs = set()
    for field in PAGE_BODY_FIELDS:
        refs.update(extract_media_refs_from_page(getattr(instance, field, None)))
    if not refs:
        return 0

    def cleanup():
        for ref in refs:
            if ref.storage == "default":
                _delete_if_unreferenced(ref.path)

    transaction.on_commit(cleanup)
    return len(refs)


def cleanup_pending_paths(items):
    deleted = 0
    for item in items:
        path = str((item or {}).get("path") or "").strip()
        if _is_managed_path(path):
            before = default_storage.exists(path)
            _delete_if_unreferenced(path)
            if before and not default_storage.exists(path):
                deleted += 1
    return deleted

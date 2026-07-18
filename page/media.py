"""Upload i validacija medija za visual builder."""

from __future__ import annotations

from dataclasses import dataclass

from django.core.files.storage import storages
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

ALLOWED_IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    }
)
ALLOWED_VIDEO_CONTENT_TYPES = frozenset(
    {
        "video/mp4",
        "video/webm",
        "video/quicktime",
    }
)
MAX_IMAGE_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_VIDEO_UPLOAD_BYTES = 200 * 1024 * 1024
EDITOR_IMAGE_UPLOAD_TO = "page/images/%Y/%m/"
PAGE_VIDEO_UPLOAD_TO = "page/videos/%Y/%m/"
PAGE_POSTER_UPLOAD_TO = "page/posters/%Y/%m/"


class EditorMediaError(Exception):
    """Greška pri obradi medija u editoru."""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or code
        super().__init__(self.message)


@dataclass(frozen=True)
class EditorImageUploadResult:
    path: str
    url: str
    alt: str = ""


@dataclass(frozen=True)
class EditorVideoUploadResult:
    path: str
    url: str


class EditorMediaService:
    """Servis za upload slika i videa iz visual buildera."""

    allowed_image_content_types = ALLOWED_IMAGE_CONTENT_TYPES
    allowed_video_content_types = ALLOWED_VIDEO_CONTENT_TYPES
    max_image_upload_bytes = MAX_IMAGE_UPLOAD_BYTES
    max_video_upload_bytes = MAX_VIDEO_UPLOAD_BYTES
    image_upload_to_template = EDITOR_IMAGE_UPLOAD_TO
    video_upload_to_template = PAGE_VIDEO_UPLOAD_TO
    poster_upload_to_template = PAGE_POSTER_UPLOAD_TO

    def validate_image(self, upload: UploadedFile) -> None:
        if upload is None:
            raise EditorMediaError("missing_image")

        if upload.size > self.max_image_upload_bytes:
            raise EditorMediaError("file_too_large")

        content_type = (upload.content_type or "").lower()
        if content_type not in self.allowed_image_content_types:
            raise EditorMediaError("invalid_content_type")

        try:
            upload.seek(0)
            with Image.open(upload) as image:
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise EditorMediaError("invalid_image") from exc
        finally:
            upload.seek(0)

    def validate_video(self, upload: UploadedFile) -> None:
        if upload is None:
            raise EditorMediaError("missing_video")

        if upload.size > self.max_video_upload_bytes:
            raise EditorMediaError("file_too_large")

        content_type = (upload.content_type or "").lower()
        if content_type not in self.allowed_video_content_types:
            raise EditorMediaError("invalid_content_type")

    def _image_upload_template_for(self, upload: UploadedFile) -> str:
        name = str(getattr(upload, "name", "") or "")
        if name.startswith("video-poster-"):
            return self.poster_upload_to_template
        return self.image_upload_to_template

    def save_image(self, upload: UploadedFile) -> str:
        self.validate_image(upload)
        storage = storages["default"]
        upload_prefix = timezone.now().strftime(self._image_upload_template_for(upload))
        return storage.save(f"{upload_prefix}{upload.name}", upload)

    def save_video(self, upload: UploadedFile) -> str:
        self.validate_video(upload)
        storage = storages["default"]
        upload_prefix = timezone.now().strftime(self.video_upload_to_template)
        return storage.save(f"{upload_prefix}{upload.name}", upload)

    def build_public_url(self, path: str, *, request=None, storage_alias: str = "default") -> str:
        storage = storages[storage_alias]
        url = storage.url(path)
        if request is not None and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url

    def resolve_existing_path(
        self,
        path: str,
        *,
        request=None,
        allowed_prefixes: tuple[str, ...] = ("page/images/", "page/posters/"),
    ) -> EditorImageUploadResult:
        cleaned = str(path or "").strip().replace("\\", "/")
        while cleaned.startswith("/"):
            cleaned = cleaned[1:]
        if (
            not cleaned
            or cleaned.startswith(("http://", "https://"))
            or ".." in cleaned.split("/")
        ):
            raise EditorMediaError("invalid_path")
        if not any(cleaned.startswith(prefix) for prefix in allowed_prefixes):
            raise EditorMediaError("unsupported_path")
        storage = storages["default"]
        if not storage.exists(cleaned):
            raise EditorMediaError("missing_file")
        try:
            with storage.open(cleaned, "rb") as handle:
                with Image.open(handle) as image:
                    image.verify()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise EditorMediaError("invalid_image") from exc
        return EditorImageUploadResult(
            path=cleaned,
            url=self.build_public_url(cleaned, request=request),
            alt="",
        )

    def build_public_url_or_rollback(
        self,
        path: str,
        *,
        request=None,
        storage_alias: str = "default",
    ) -> str:
        """Ne ostavlja upload u storage-u ako URL ne može da se generiše."""
        try:
            return self.build_public_url(
                path,
                request=request,
                storage_alias=storage_alias,
            )
        except Exception:
            try:
                storages[storage_alias].delete(path)
            except Exception:
                pass
            raise

    def upload_image(self, upload: UploadedFile, *, request=None) -> EditorImageUploadResult:
        path = self.save_image(upload)
        alt = ""
        name = getattr(upload, "name", "") or ""
        if name:
            from pathlib import Path

            alt = Path(name).stem.replace("_", " ").replace("-", " ").strip()
        return EditorImageUploadResult(
            path=path,
            url=self.build_public_url_or_rollback(
                path,
                request=request,
                storage_alias="default",
            ),
            alt=alt,
        )

    def upload_video(self, upload: UploadedFile, *, request=None) -> EditorVideoUploadResult:
        path = self.save_video(upload)
        return EditorVideoUploadResult(
            path=path,
            url=self.build_public_url_or_rollback(
                path,
                request=request,
                storage_alias="default",
            ),
        )

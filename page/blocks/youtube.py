"""YouTube URL helpers za video blok."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

_YOUTUBE_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "youtu.be",
        "www.youtu.be",
        "youtube-nocookie.com",
        "www.youtube-nocookie.com",
    }
)


def is_youtube_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url.strip())
    host = (parsed.netloc or "").lower()
    if host in _YOUTUBE_HOSTS:
        return True
    return host.endswith(".youtube.com")


def youtube_embed_src(url: str) -> str:
    if not url:
        return ""

    parsed = urlparse(url.strip())
    host = (parsed.netloc or "").lower()
    path = parsed.path or ""

    if "/embed/" in path:
        return url.strip()

    video_id = ""
    if "youtu.be" in host:
        video_id = path.strip("/").split("/")[0]
    else:
        query = parse_qs(parsed.query)
        if "v" in query and query["v"]:
            video_id = query["v"][0]
        elif path.startswith("/shorts/"):
            parts = path.split("/")
            video_id = parts[2] if len(parts) > 2 else ""

    if not video_id:
        return url.strip()

    return f"https://www.youtube.com/embed/{video_id}"

"""Robots meta tag — index/follow, nosnippet, noarchive, max-image-preview."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from seo.constants import RobotsMaxImagePreview, RobotsMaxSnippet
from seo.models import SeoMetadata


def build_robots_meta_content(
    *,
    robots_index: bool = True,
    robots_follow: bool = True,
    robots_nosnippet: bool = False,
    robots_noarchive: bool = False,
    robots_max_image_preview: str = RobotsMaxImagePreview.AUTO,
    robots_max_snippet: str = RobotsMaxSnippet.AUTO,
) -> str:
    """
    Gradi vrednost za <meta name="robots" content="...">.

    Redosled direktiva prati Google preporuke: index/noindex, follow/nofollow,
    zatim opcione direktive (nosnippet, noarchive, max-snippet, max-image-preview).
    """
    parts: list[str] = [
        "index" if robots_index else "noindex",
        "follow" if robots_follow else "nofollow",
    ]

    if robots_nosnippet:
        parts.append("nosnippet")

    if robots_noarchive:
        parts.append("noarchive")

    snippet = str(robots_max_snippet if robots_max_snippet is not None else "").strip()
    if snippet and snippet != RobotsMaxSnippet.AUTO:
        parts.append(f"max-snippet:{snippet}")

    preview = str(robots_max_image_preview or RobotsMaxImagePreview.AUTO).strip()
    if preview and preview != RobotsMaxImagePreview.AUTO:
        parts.append(f"max-image-preview:{preview}")

    return ", ".join(parts)


def resolve_robots_directive(metadata: SeoMetadata | None) -> str:
    """Vraća robots content string za šablone i SEO kontekst."""
    if metadata is None:
        return build_robots_meta_content()

    return build_robots_meta_content(
        robots_index=metadata.robots_index,
        robots_follow=metadata.robots_follow,
        robots_nosnippet=metadata.robots_nosnippet,
        robots_noarchive=metadata.robots_noarchive,
        robots_max_image_preview=metadata.robots_max_image_preview,
        robots_max_snippet=metadata.robots_max_snippet,
    )


@dataclass(frozen=True)
class RobotsPreview:
    content: str
    meta_tag: str
    directives: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def build_robots_preview(metadata: SeoMetadata | None = None, **overrides) -> RobotsPreview:
    """Pregled robots meta taga za CMS."""
    values = {
        "robots_index": True,
        "robots_follow": True,
        "robots_nosnippet": False,
        "robots_noarchive": False,
        "robots_max_image_preview": RobotsMaxImagePreview.AUTO,
        "robots_max_snippet": RobotsMaxSnippet.AUTO,
    }
    if metadata is not None:
        values.update(
            {
                "robots_index": metadata.robots_index,
                "robots_follow": metadata.robots_follow,
                "robots_nosnippet": metadata.robots_nosnippet,
                "robots_noarchive": metadata.robots_noarchive,
                "robots_max_image_preview": metadata.robots_max_image_preview,
                "robots_max_snippet": metadata.robots_max_snippet,
            }
        )
    values.update({key: value for key, value in overrides.items() if value is not None})

    content = build_robots_meta_content(**values)
    directives = [part.strip() for part in content.split(",") if part.strip()]
    meta_tag = f'<meta name="robots" content="{content}">'

    return RobotsPreview(
        content=content,
        meta_tag=meta_tag,
        directives=directives,
    )

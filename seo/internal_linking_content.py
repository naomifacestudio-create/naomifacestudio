"""Izvlačenje internih linkova iz buildera i indeks blog članaka."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from django.contrib.contenttypes.models import ContentType

from blogs.models import BlogPost
from seo.content_text import normalize_whitespace
from seo.models import SeoMetadata
from seo.services import resolve_seo_title

_LINK_HREF_RE = re.compile(
    r"""<a\b[^>]*\bhref\s*=\s*(['"])(.*?)\1""",
    re.IGNORECASE | re.DOTALL,
)
_ANCHOR_TEXT_RE = re.compile(
    r"""<a\b[^>]*>(.*?)</a>""",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value: str) -> str:
    return normalize_whitespace(_TAG_RE.sub(" ", value or ""))


@dataclass(frozen=True)
class InternalLink:
    href: str
    anchor_text: str
    source: str


@dataclass(frozen=True)
class ArticleLinkTarget:
    post_id: int
    title: str
    slug: str
    url_path: str
    focus_keyword: str
    secondary_keywords: tuple[str, ...]
    category_id: int | None
    is_cornerstone: bool
    link_phrases: tuple[str, ...]


def normalize_internal_href(href: str) -> str | None:
    if not href or not href.strip():
        return None

    raw = href.strip()
    if "://" in raw:
        path = urlparse(raw).path or "/"
    else:
        path = raw.split("?")[0].split("#")[0]

    if not path.startswith("/"):
        path = f"/{path}"

    normalized = path.rstrip("/") or "/"
    return normalized


def href_matches_post_slug(href: str, slug: str) -> bool:
    path = normalize_internal_href(href)
    if not path or not slug:
        return False
    slug = slug.strip("/")
    return path == f"/blog/{slug}" or path.endswith(f"/blog/{slug}")


def extract_links_from_html(html: str) -> list[tuple[str, str]]:
    if not html:
        return []

    pairs: list[tuple[str, str]] = []
    for href_match in _LINK_HREF_RE.finditer(html):
        href = href_match.group(2).strip()
        anchor = ""
        tail = html[href_match.end() :]
        anchor_match = _ANCHOR_TEXT_RE.match(tail)
        if anchor_match:
            anchor = _strip_html(anchor_match.group(1)).strip()
        pairs.append((href, anchor))
    return pairs


def extract_internal_links_from_object(
    page_object,
    *,
    visible_only: bool = False,
) -> list[InternalLink]:
    if page_object is None or not getattr(page_object, "pk", None):
        return []

    links: list[InternalLink] = []

    should_render_page = getattr(page_object, "should_render_page", None)
    if callable(should_render_page) and should_render_page():
        from page.constants import BlockType as PageBlockType

        body_page = getattr(page_object, "body_page", None) or {}
        for section in body_page.get("sections") or []:
            for row in section.get("rows") or []:
                for column in row.get("columns") or []:
                    for block in column.get("blocks") or []:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") != PageBlockType.BUTTON:
                            continue
                        attrs = block.get("attrs") or {}
                        href = str(attrs.get("href", "")).strip()
                        if href and _is_internal_href(href):
                            links.append(
                                InternalLink(
                                    href=href,
                                    anchor_text=str(attrs.get("label", "")).strip(),
                                    source="button",
                                )
                            )
        return links

    return links


def _is_internal_href(href: str) -> bool:
    path = normalize_internal_href(href)
    if not path:
        return False
    return path.startswith("/blog/") or "/blog/" in path


def _title_phrases(title: str) -> list[str]:
    words = normalize_whitespace(title).split()
    if len(words) <= 6:
        return [title.strip()] if title.strip() else []
    return [" ".join(words[:4]), " ".join(words[:6])]


def _build_link_phrases(
    title: str,
    focus_keyword: str,
    secondary_keywords: list[str],
) -> tuple[str, ...]:
    phrases: list[str] = []
    seen: set[str] = set()

    def add(phrase: str) -> None:
        cleaned = normalize_whitespace(phrase).strip()
        key = cleaned.lower()
        if cleaned and key not in seen and len(cleaned) >= 3:
            seen.add(key)
            phrases.append(cleaned)

    if focus_keyword:
        add(focus_keyword)
    for keyword in secondary_keywords:
        add(keyword)
    add(title)
    for phrase in _title_phrases(title):
        add(phrase)

    return tuple(phrases)


def _load_index_posts(*, exclude_pk: int | None = None, include_pk: int | None = None):
    posts = BlogPost.objects.publicly_visible().only(
        "id", "title_hr", "title_en", "slug_hr", "slug_en"
    )
    if exclude_pk:
        posts = posts.exclude(pk=exclude_pk)

    post_list = list(posts)
    if include_pk and not any(post.pk == include_pk for post in post_list):
        extra = (
            BlogPost.objects.filter(pk=include_pk)
            .only("id", "title_hr", "title_en", "slug_hr", "slug_en")
            .first()
        )
        if extra is not None:
            post_list.append(extra)
    return post_list


def _targets_from_posts(post_list: list[BlogPost]) -> list[ArticleLinkTarget]:
    if not post_list:
        return []

    content_type = ContentType.objects.get_for_model(BlogPost)
    # Prefer Croatian SEO profiles for the linking index (site default locale).
    metadata_by_post_id = {}
    for metadata in SeoMetadata.objects.filter(
        content_type=content_type,
        object_id__in=[post.pk for post in post_list],
    ):
        existing = metadata_by_post_id.get(metadata.object_id)
        if existing is None or getattr(metadata, "locale", "") == "hr":
            metadata_by_post_id[metadata.object_id] = metadata

    targets: list[ArticleLinkTarget] = []
    for post in post_list:
        metadata = metadata_by_post_id.get(post.pk)
        focus_keyword = metadata.focus_keyword.strip() if metadata else ""
        secondary = metadata.secondary_keywords_list if metadata else []
        title = resolve_seo_title(post, metadata)
        targets.append(
            ArticleLinkTarget(
                post_id=post.pk,
                title=title,
                slug=post.slug,
                url_path=post.get_absolute_url(),
                focus_keyword=focus_keyword,
                secondary_keywords=tuple(secondary),
                category_id=getattr(post, "category_id", None),
                is_cornerstone=bool(metadata and metadata.is_cornerstone),
                link_phrases=_build_link_phrases(title, focus_keyword, secondary),
            )
        )

    return targets


def build_article_link_index(
    *,
    exclude_pk: int | None = None,
    include_pk: int | None = None,
) -> list[ArticleLinkTarget]:
    return _targets_from_posts(_load_index_posts(exclude_pk=exclude_pk, include_pk=include_pk))


@dataclass(frozen=True)
class SiteLinkGraph:
    targets_by_id: dict[int, ArticleLinkTarget]
    outgoing: dict[int, set[int]]
    incoming: dict[int, set[int]]


def build_site_link_graph(*, include_pk: int | None = None) -> SiteLinkGraph:
    post_list = _load_index_posts(include_pk=include_pk)
    targets = _targets_from_posts(post_list)
    targets_by_id = {target.post_id: target for target in targets}
    slug_to_id = {target.slug: target.post_id for target in targets}

    outgoing: dict[int, set[int]] = {post_id: set() for post_id in targets_by_id}
    incoming: dict[int, set[int]] = {post_id: set() for post_id in targets_by_id}

    for post in post_list:
        links = extract_internal_links_from_object(post, visible_only=False)
        for link in links:
            for slug, target_id in slug_to_id.items():
                if href_matches_post_slug(link.href, slug):
                    if target_id != post.pk:
                        outgoing[post.pk].add(target_id)
                        incoming[target_id].add(post.pk)
                    break

    return SiteLinkGraph(
        targets_by_id=targets_by_id,
        outgoing=outgoing,
        incoming=incoming,
    )


def resolve_linked_post_ids(
    links: list[InternalLink],
    targets: list[ArticleLinkTarget],
) -> set[int]:
    slug_by_id = {target.post_id: target.slug for target in targets}
    linked_ids: set[int] = set()

    for link in links:
        for post_id, slug in slug_by_id.items():
            if href_matches_post_slug(link.href, slug):
                linked_ids.add(post_id)
                break

    return linked_ids

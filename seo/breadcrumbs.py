"""SEO breadcrumb trail — hijerarhija, automatsko generisanje i JSON-LD."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.urls import NoReverseMatch, reverse

from blogs.models import BlogCategory, BlogPost
from core.models import CMSPage
from seo.schema.base import JSON_LD_CONTEXT, absolute_url, clean_schema


@dataclass(frozen=True)
class BreadcrumbItem:
    title: str
    url: str | None = None
    url_name: str | None = None
    url_kwargs: dict[str, Any] = field(default_factory=dict)

    @property
    def is_current(self) -> bool:
        return not self.url and not self.url_name


@dataclass
class BreadcrumbTrail:
    items: list[BreadcrumbItem] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.items)

    def resolve_urls(self, request) -> list[tuple[str, str | None]]:
        """Vraća (title, absolute_url) — poslednja stavka uvek ima URL za schema.org."""
        resolved: list[tuple[str, str | None]] = []
        current_canonical = ""

        for item in self.items:
            url = item.url
            if not url and item.url_name:
                try:
                    path = reverse(item.url_name, kwargs=item.url_kwargs or None)
                    url = absolute_url(request, path)
                except NoReverseMatch:
                    url = None
            if item.is_current and not url:
                url = current_canonical or None
            if url and item.is_current:
                current_canonical = url
            resolved.append((item.title, url))

        return resolved


def _home_item() -> BreadcrumbItem:
    for name in ("home", "frontend:home"):
        try:
            reverse(name)
            return BreadcrumbItem(
                title=getattr(settings, "BREADCRUMB_HOME_TITLE", "Početna"),
                url_name=name,
            )
        except NoReverseMatch:
            continue
    return BreadcrumbItem(
        title=getattr(settings, "BREADCRUMB_HOME_TITLE", "Početna"),
        url="/",
    )


def _blog_index_item() -> BreadcrumbItem:
    for name in ("blog_list", "frontend:blog"):
        try:
            reverse(name)
            return BreadcrumbItem(
                title=getattr(settings, "BREADCRUMB_BLOG_TITLE", "Blog"),
                url_name=name,
            )
        except NoReverseMatch:
            continue
    return BreadcrumbItem(
        title=getattr(settings, "BREADCRUMB_BLOG_TITLE", "Blog"),
        url="/",
    )


def build_trail_for_blog_post(request, post: BlogPost) -> BreadcrumbTrail:
    items = [_home_item(), _blog_index_item()]

    category = getattr(post, "category", None)
    if category is not None and getattr(category, "is_active", False):
        get_ancestors = getattr(category, "get_ancestors", None)
        ancestors = get_ancestors() if callable(get_ancestors) else []
        for ancestor in ancestors:
            items.append(
                BreadcrumbItem(
                    title=ancestor.get_breadcrumb_title(),
                    url_name="frontend:blog_category",
                    url_kwargs={"category_path": ancestor.get_slug_path()},
                )
            )
        get_bc = getattr(category, "get_breadcrumb_title", None)
        get_path = getattr(category, "get_slug_path", None)
        if callable(get_bc) and callable(get_path):
            items.append(
                BreadcrumbItem(
                    title=get_bc(),
                    url_name="frontend:blog_category",
                    url_kwargs={"category_path": get_path()},
                )
            )

    title = ""
    if hasattr(post, "get_breadcrumb_title"):
        title = post.get_breadcrumb_title()
    else:
        from seo.services import resolve_breadcrumb_title

        title = resolve_breadcrumb_title(post)

    url = ""
    if hasattr(post, "get_canonical_url"):
        url = post.get_canonical_url(request)
    elif hasattr(post, "get_absolute_url"):
        from seo.schema.base import absolute_url as abs_url

        url = abs_url(request, post.get_absolute_url()) if request else post.get_absolute_url()

    items.append(BreadcrumbItem(title=title, url=url))
    return BreadcrumbTrail(items=items)


def build_trail_for_blog_category(request, category: BlogCategory) -> BreadcrumbTrail:
    items = [_home_item(), _blog_index_item()]
    for ancestor in category.get_ancestors():
        items.append(
            BreadcrumbItem(
                title=ancestor.get_breadcrumb_title(),
                url_name="frontend:blog_category",
                url_kwargs={"category_path": ancestor.get_slug_path()},
            )
        )
    items.append(
        BreadcrumbItem(
            title=category.get_breadcrumb_title(),
            url=category.get_canonical_url(request),
        )
    )
    return BreadcrumbTrail(items=items)


def build_trail_for_cms_page(request, page: CMSPage) -> BreadcrumbTrail:
    items = [_home_item()]
    if page.page_type == CMSPage.PageType.PROJEKTI:
        items.append(
            BreadcrumbItem(
                title=page.get_breadcrumb_title(),
                url=page.get_canonical_url(request),
            )
        )
    else:
        items.append(
            BreadcrumbItem(
                title=page.get_breadcrumb_title(),
                url=page.get_canonical_url(request),
            )
        )
    return BreadcrumbTrail(items=items)


def build_trail_for_static_page(
    request,
    *,
    title: str,
    url_name: str,
    url_kwargs: dict[str, Any] | None = None,
) -> BreadcrumbTrail:
    path = reverse(url_name, kwargs=url_kwargs or None)
    return BreadcrumbTrail(
        items=[
            _home_item(),
            BreadcrumbItem(
                title=title,
                url=absolute_url(request, path),
            ),
        ]
    )


def build_trail_from_override(request, items: list[dict[str, Any]]) -> BreadcrumbTrail:
    trail_items: list[BreadcrumbItem] = []
    for raw in items:
        trail_items.append(
            BreadcrumbItem(
                title=str(raw.get("title", "")).strip(),
                url=raw.get("url"),
                url_name=raw.get("url_name"),
                url_kwargs=raw.get("url_kwargs") or {},
            )
        )
    return BreadcrumbTrail(items=[item for item in trail_items if item.title])


def resolve_breadcrumb_trail(
    request,
    *,
    seo_object=None,
    breadcrumbs_override: list[dict[str, Any]] | None = None,
) -> BreadcrumbTrail:
    if breadcrumbs_override:
        return build_trail_from_override(request, breadcrumbs_override)

    if isinstance(seo_object, BlogPost):
        return build_trail_for_blog_post(request, seo_object)

    if isinstance(seo_object, BlogCategory):
        return build_trail_for_blog_category(request, seo_object)

    if isinstance(seo_object, CMSPage):
        return build_trail_for_cms_page(request, seo_object)

    if request and getattr(request, "resolver_match", None):
        url_name = request.resolver_match.url_name
        if url_name == "blog":
            return build_trail_for_static_page(
                request,
                title=getattr(settings, "BREADCRUMB_BLOG_TITLE", "Blog"),
                url_name="frontend:blog",
            )
        if url_name == "usluge":
            return build_trail_for_static_page(request, title="Usluge", url_name="frontend:usluge")
        if url_name == "kontakt":
            return build_trail_for_static_page(request, title="Kontakt", url_name="frontend:kontakt")

    return BreadcrumbTrail()


def trail_to_breadcrumb_schema(
    request,
    trail: BreadcrumbTrail,
    *,
    page_url: str | None = None,
) -> dict[str, Any] | None:
    if not trail:
        return None

    resolved = trail.resolve_urls(request)
    if len(resolved) < 2:
        return None

    elements: list[dict[str, Any]] = []
    last_url = page_url

    for index, (title, url) in enumerate(resolved, start=1):
        item_url = url or last_url
        if not item_url:
            continue
        last_url = item_url
        elements.append(
            {
                "@type": "ListItem",
                "position": index,
                "name": title,
                "item": item_url,
            }
        )

    if len(elements) < 2 or not last_url:
        return None

    return clean_schema(
        {
            "@context": JSON_LD_CONTEXT,
            "@type": "BreadcrumbList",
            "@id": f"{last_url}#breadcrumb",
            "itemListElement": elements,
        }
    )

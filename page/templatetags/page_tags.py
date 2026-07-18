from django import template
from django.utils.safestring import mark_safe

from page.rendering import get_page_renderer
from page.rendering.context import build_render_context_for_post

register = template.Library()


def _render_page_content(context, host):
    if host is None or not host.has_page_content():
        return ""

    request = context.get("request")
    render_context = build_render_context_for_post(
        host,
        request=request,
        preview_mode=bool(context.get("is_admin_preview")),
        visible_only=not bool(context.get("is_admin_preview")),
    )
    renderer = get_page_renderer("html")
    html = renderer.render(host.get_body_page(), context=render_context)
    return mark_safe(html)


@register.simple_tag(takes_context=True)
def render_page_content(context, content):
    """Renderuje iv_page_v1 sadržaj objekta."""
    return _render_page_content(context, content)


@register.simple_tag(takes_context=True)
def render_cms_page(context, page):
    """Renderuje iv_page_v1 sadržaj CMS stranice."""
    return _render_page_content(context, page)


@register.simple_tag(takes_context=True)
def render_localized_page(context, content):
    return _render_page_content(context, content)

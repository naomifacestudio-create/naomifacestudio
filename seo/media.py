"""SEO slike — istaknuta slika ili page JSON sadržaj."""

from seo.helpers import get_image_dimensions, resolve_absolute_url

__all__ = ("get_image_dimensions", "get_page_seo_image", "apply_seo_image_to_context")


def get_page_seo_image(page_object, request=None, *, visible_only=True):
    """
    Vraća (apsolutni_url, širina, visina).
    Prvo istaknuta slika, zatim prva slika iz page JSON-a.
    """
    _ = visible_only
    featured = getattr(page_object, "featured_image", None)
    if featured and getattr(featured, "name", ""):
        url = resolve_absolute_url(request, featured.url)
        width, height = get_image_dimensions(featured)
        return url, width, height

    from seo.image_seo_content import get_first_page_image_src

    should_render_page = getattr(page_object, "should_render_page", None)
    if callable(should_render_page) and should_render_page():
        page_src = get_first_page_image_src(page_object)
        if page_src:
            url = resolve_absolute_url(request, page_src)
            return url or page_src, None, None

    return "", None, None


def apply_seo_image_to_context(page_object, context, request, *, visible_only=True):
    """Dopunjava SEO kontekst slikom i dimenzijama za Open Graph."""
    image_url, width, height = get_page_seo_image(
        page_object,
        request,
        visible_only=visible_only,
    )
    if not image_url:
        return context

    context["og_image"] = image_url
    context["twitter_image"] = image_url
    context["twitter_card"] = "summary_large_image"
    if width and height:
        context["og_image_width"] = width
        context["og_image_height"] = height
    return context

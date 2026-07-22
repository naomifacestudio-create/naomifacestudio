"""Mali SEO pomoćnici bez zavisnosti od servisa ili modela."""

from seo.canonical import build_absolute_canonical


def resolve_absolute_url(request, url: str | None) -> str | None:
    return build_absolute_canonical(url, request)


def get_image_dimensions(image_field):
    if not image_field or not getattr(image_field, "name", ""):
        return None, None

    width = getattr(image_field, "width", None)
    height = getattr(image_field, "height", None)
    if width and height:
        return int(width), int(height)
    return None, None

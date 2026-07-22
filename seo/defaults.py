from django.conf import settings

from seo.canonical import resolve_request_canonical


def get_site_seo_defaults(request=None):
    """Default SEO when a page has no seo_object."""
    site_name = getattr(settings, "SEO_SITE_NAME", "Naomi Face Studio")
    title = getattr(
        settings,
        "SEO_DEFAULT_TITLE",
        f"{site_name} — Premium facial treatments & education",
    )
    description = getattr(
        settings,
        "SEO_DEFAULT_DESCRIPTION",
        "Naomi Face Studio - Premium facial treatments, education and professional skincare.",
    )
    canonical = resolve_request_canonical(request) if request else None

    og_image = getattr(settings, "SEO_DEFAULT_OG_IMAGE_URL", None)
    if not og_image:
        from django.templatetags.static import static

        og_image = static("images/naomi_first_image_home.webp")
    if og_image and request and og_image.startswith("/"):
        from seo.canonical import build_absolute_canonical

        og_image = build_absolute_canonical(og_image, request)

    return {
        "title": title,
        "description": description,
        "canonical": canonical,
        "og_url": canonical,
        "robots": "index, follow",
        "og_type": "website",
        "og_title": title,
        "og_description": description,
        "og_image": og_image,
        "twitter_card": "summary_large_image" if og_image else "summary",
        "twitter_title": title,
        "twitter_description": description,
        "twitter_image": og_image,
    }

from django.templatetags.static import static
from django.utils.translation import gettext as _


def site_seo(request):
    title = _("Naomi Face Studio")
    description = _(
        "Naomi Face Studio - Premium facial treatments, education and professional skincare."
    )
    canonical = request.build_absolute_uri(request.path)
    image = request.build_absolute_uri(static("images/naomi_first_image_home.webp"))
    return {
        "seo": {
            "title": title,
            "description": description,
            "canonical": canonical,
            "robots": "index, follow",
            "og_title": title,
            "og_description": description,
            "og_image": image,
            "og_type": "website",
            "og_url": canonical,
            "twitter_title": title,
            "twitter_description": description,
            "twitter_image": image,
            "twitter_card": "summary_large_image",
        }
    }

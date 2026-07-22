from django.conf import settings
from django.http import HttpResponse


def robots_txt(request):
    """robots.txt sa referencom na sitemap."""
    lines = ["User-agent: *"]

    if getattr(settings, "SEO_DISALLOW_ALL", False):
        lines.append("Disallow: /")
    else:
        lines.extend(
            [
                "Disallow: /admin/",
                "Disallow: /django-admin/",
                "Allow: /",
            ]
        )

    sitemap_url = request.build_absolute_uri(reverse_sitemap())
    lines.append(f"Sitemap: {sitemap_url}")

    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def reverse_sitemap():
    from django.urls import reverse

    return reverse("sitemap")

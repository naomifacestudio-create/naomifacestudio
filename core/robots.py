from django.http import HttpResponse


def robots_txt(request):
    site_url = request.build_absolute_uri("/").rstrip("/")
    content = f"""User-agent: *
Allow: /

# Disallow admin and private areas
Disallow: /admin/
Disallow: /i18n/

# Sitemap
Sitemap: {site_url}/sitemap.xml
"""
    return HttpResponse(content, content_type="text/plain")

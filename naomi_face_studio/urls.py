"""
URL configuration for naomi_face_studio project.
"""
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _

from core.robots import robots_txt
from core.views import localized_set_language
from core.sitemaps import sitemaps

# Customize admin site header and title
admin.site.site_header = 'Naomi Face Studio'
admin.site.site_title = 'Naomi Face Studio'
admin.site.index_title = _('Site Administration')


def redirect_legacy_hr_urls(request, rest=''):
    """Keep old /hr/... bookmarks working after the Serbian Latin locale switch."""
    target = f'/sr-latn/{rest}' if rest else '/sr-latn/'
    query = request.META.get('QUERY_STRING')
    if query:
        target = f'{target}?{query}'
    return redirect(target, permanent=True)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('i18n/setlang/', localized_set_language, name='set_language'),
    re_path(r'^hr/(?P<rest>.*)$', redirect_legacy_hr_urls),
]

urlpatterns += i18n_patterns(
    path('', include('core.urls')),
    path('treatments/', include('treatments.urls')),
    path('education/', include('education.urls')),
    path('blogs/', include('blogs.urls')),
    path('reservations/', include('reservations.urls')),
    path('gift-vouchers/', include('gift_vouchers.urls')),
    path('contact/', include('contacts.urls')),
    prefix_default_language=True,
)

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


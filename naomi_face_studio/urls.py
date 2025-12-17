"""
URL configuration for naomi_face_studio project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import set_language
from django.utils.translation import gettext_lazy as _

# Customize admin site header and title
admin.site.site_header = 'Naomi Face Studio'
admin.site.site_title = 'Naomi Face Studio'
admin.site.index_title = _('Site Administration')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('i18n/setlang/', set_language, name='set_language'),
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


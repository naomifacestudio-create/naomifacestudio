from ckeditor_uploader.fields import RichTextUploadingField
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.i18n_utils import active_language_code


def blog_thumbnail_upload_path(instance, filename):
    """Generate upload path for blog thumbnails - keeps original filename"""
    return f"blogs/thumbnails/{filename}"


class Blog(models.Model):
    # Croatian fields
    title_hr = models.CharField(_('Title (Croatian)'), max_length=200)
    slug_hr = models.SlugField(_('Slug (Croatian)'), max_length=200, unique=True)
    short_description_hr = models.TextField(_('Short Description (Croatian)'), max_length=500)
    full_description_hr = RichTextUploadingField(_('Full Description (Croatian)'))
    meta_description_hr = models.CharField(_('Meta Description (Croatian)'), max_length=160, blank=True)
    
    # English fields
    title_en = models.CharField(_('Title (English)'), max_length=200)
    slug_en = models.SlugField(_('Slug (English)'), max_length=200, unique=True)
    short_description_en = models.TextField(_('Short Description (English)'), max_length=500)
    full_description_en = RichTextUploadingField(_('Full Description (English)'))
    meta_description_en = models.CharField(_('Meta Description (English)'), max_length=160, blank=True)
    
    # Common fields
    thumbnail = models.ImageField(_('Thumbnail Image'), upload_to=blog_thumbnail_upload_path, help_text=_('Supports WebP format'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(_('Active'), default=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Blog')
        verbose_name_plural = _('Blogs')
    
    def __str__(self):
        return self.title_hr
    
    def get_absolute_url(self, language_code=None):
        """Get absolute URL for blog (uses active locale when language_code is omitted)."""
        language_code = active_language_code(language_code)
        if language_code == 'en':
            slug = self.slug_en
        else:
            slug = self.slug_hr
        return reverse('blogs:detail', kwargs={'slug': slug})
    
    def get_title(self, language_code=None):
        """Get title in specified language (active locale when omitted)."""
        language_code = active_language_code(language_code)
        return getattr(self, f'title_{language_code}', self.title_hr)
    
    def get_slug(self, language_code=None):
        """Get slug in specified language (active locale when omitted)."""
        language_code = active_language_code(language_code)
        return getattr(self, f'slug_{language_code}', self.slug_hr)
    
    def get_short_description(self, language_code=None):
        """Get short description in specified language (active locale when omitted)."""
        language_code = active_language_code(language_code)
        return getattr(self, f'short_description_{language_code}', self.short_description_hr)
    
    def get_full_description(self, language_code=None):
        """Get full description in specified language (active locale when omitted)."""
        language_code = active_language_code(language_code)
        return getattr(self, f'full_description_{language_code}', self.full_description_hr)
    
    def get_meta_description(self, language_code=None):
        """Get meta description in specified language (active locale when omitted)."""
        language_code = active_language_code(language_code)
        return getattr(self, f'meta_description_{language_code}', self.meta_description_hr) or self.get_short_description(language_code)


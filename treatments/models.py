from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from ckeditor_uploader.fields import RichTextUploadingField
from django.core.validators import MinValueValidator
import os


def treatment_thumbnail_upload_path(instance, filename):
    """Generate upload path for treatment thumbnails - keeps original filename"""
    return f"treatments/thumbnails/{filename}"


class Treatment(models.Model):
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
    duration_hours = models.PositiveIntegerField(_('Duration (Hours)'), default=0, validators=[MinValueValidator(0)])
    duration_minutes = models.PositiveIntegerField(_('Duration (Minutes)'), default=0, validators=[MinValueValidator(0)])
    pause_hours = models.PositiveIntegerField(_('Pause After Treatment (Hours)'), default=0, validators=[MinValueValidator(0)], help_text=_('Rest time needed after this treatment (not visible to users)'))
    pause_minutes = models.PositiveIntegerField(_('Pause After Treatment (Minutes)'), default=0, validators=[MinValueValidator(0)], help_text=_('Rest time needed after this treatment (not visible to users)'))
    price = models.DecimalField(_('Price'), max_digits=10, decimal_places=2)
    thumbnail = models.ImageField(_('Thumbnail Image'), upload_to=treatment_thumbnail_upload_path, help_text=_('Supports WebP format'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(_('Active'), default=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Treatment')
        verbose_name_plural = _('Treatments')
    
    def __str__(self):
        return self.title_hr
    
    def get_absolute_url(self, language_code='hr'):
        """Get absolute URL for treatment"""
        if language_code == 'en':
            slug = self.slug_en
        else:
            slug = self.slug_hr
        return reverse('treatments:detail', kwargs={'slug': slug})
    
    def get_duration_display(self):
        """Get formatted duration"""
        parts = []
        if self.duration_hours > 0:
            parts.append(f"{self.duration_hours}h")
        if self.duration_minutes > 0:
            parts.append(f"{self.duration_minutes}min")
        return " ".join(parts) if parts else "0min"
    
    def get_total_minutes(self):
        """Get total duration in minutes"""
        return (self.duration_hours * 60) + self.duration_minutes
    
    def get_total_pause_minutes(self):
        """Get total pause time in minutes"""
        return (self.pause_hours * 60) + self.pause_minutes
    
    def get_title(self, language_code='hr'):
        """Get title in specified language"""
        return getattr(self, f'title_{language_code}', self.title_hr)
    
    def get_slug(self, language_code='hr'):
        """Get slug in specified language"""
        return getattr(self, f'slug_{language_code}', self.slug_hr)
    
    def get_short_description(self, language_code='hr'):
        """Get short description in specified language"""
        return getattr(self, f'short_description_{language_code}', self.short_description_hr)
    
    def get_full_description(self, language_code='hr'):
        """Get full description in specified language"""
        return getattr(self, f'full_description_{language_code}', self.full_description_hr)
    
    def get_meta_description(self, language_code='hr'):
        """Get meta description in specified language"""
        return getattr(self, f'meta_description_{language_code}', self.meta_description_hr)


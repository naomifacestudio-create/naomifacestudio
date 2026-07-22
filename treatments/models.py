from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.content import BuilderContentQuerySet, LocalizedBuilderContent
from core.i18n_utils import active_language_code


def treatment_thumbnail_upload_path(instance, filename):
    """Generate upload path for treatment thumbnails - keeps original filename"""
    return f"treatments/thumbnails/{filename}"


class Treatment(LocalizedBuilderContent):
    objects = BuilderContentQuerySet.as_manager()
    duration_hours = models.PositiveIntegerField(_('Duration (Hours)'), default=0, validators=[MinValueValidator(0)])
    duration_minutes = models.PositiveIntegerField(_('Duration (Minutes)'), default=0, validators=[MinValueValidator(0)])
    pause_hours = models.PositiveIntegerField(_('Pause After Treatment (Hours)'), default=0, validators=[MinValueValidator(0)], help_text=_('Rest time needed after this treatment (not visible to users)'))
    pause_minutes = models.PositiveIntegerField(_('Pause After Treatment (Minutes)'), default=0, validators=[MinValueValidator(0)], help_text=_('Rest time needed after this treatment (not visible to users)'))
    price = models.DecimalField(_('Price'), max_digits=10, decimal_places=2)

    class Meta(LocalizedBuilderContent.Meta):
        verbose_name = _('Treatment')
        verbose_name_plural = _('Treatments')
    
    def __str__(self):
        return self.title_hr
    
    def get_absolute_url(self, language_code=None):
        """Get absolute URL for treatment (uses active locale when language_code is omitted)."""
        language_code = active_language_code(language_code)
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
    

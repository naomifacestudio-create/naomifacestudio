from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.content import LocalizedBuilderContent
from core.i18n_utils import active_language_code


def blog_thumbnail_upload_path(instance, filename):
    """Legacy upload path kept for historical migrations."""
    return f"blogs/thumbnails/{filename}"


class Blog(LocalizedBuilderContent):
    class Meta(LocalizedBuilderContent.Meta):
        verbose_name = _('Blog')
        verbose_name_plural = _('Blogs')

    def __str__(self):
        return self.title_hr

    def get_absolute_url(self, language_code=None):
        language_code = active_language_code(language_code)
        slug = self.slug_en if language_code == 'en' else self.slug_hr
        return reverse('blogs:detail', kwargs={'slug': slug})

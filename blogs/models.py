from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.content import BuilderContentQuerySet, LocalizedBuilderContent
from core.i18n_utils import active_language_code


def blog_thumbnail_upload_path(instance, filename):
    """Legacy upload path kept for historical migrations."""
    return f"blogs/thumbnails/{filename}"


class Blog(LocalizedBuilderContent):
    objects = BuilderContentQuerySet.as_manager()

    class Meta(LocalizedBuilderContent.Meta):
        verbose_name = _('Blog')
        verbose_name_plural = _('Blogs')

    def __str__(self):
        return self.title_hr

    def get_absolute_url(self, language_code=None):
        language_code = active_language_code(language_code)
        slug = self.slug_en if language_code == 'en' else self.slug_hr
        return reverse('blogs:detail', kwargs={'slug': slug})


# SEO stack compatibility alias (analyzers historically target BlogPost).
BlogPost = Blog


class _BlogCategoryEmptyQS:
    def filter(self, *a, **k):
        return self

    def select_related(self, *a, **k):
        return self

    def order_by(self, *a, **k):
        return self

    def publicly_visible(self):
        return self

    def exclude(self, *a, **k):
        return self

    def only(self, *a, **k):
        return self

    def __iter__(self):
        return iter(())

    def first(self):
        return None

    def __bool__(self):
        return False

    def __len__(self):
        return 0


class BlogCategory:
    """Non-model stub — Naomi does not ship blog categories."""

    objects = _BlogCategoryEmptyQS()
    is_active = False
    name = ""
    slug = ""
    parent = None

    def get_ancestors(self):
        return []

    def get_breadcrumb_title(self):
        return self.name

    def get_slug_path(self):
        return self.slug or ""

    def get_canonical_url(self, request=None):
        return ""

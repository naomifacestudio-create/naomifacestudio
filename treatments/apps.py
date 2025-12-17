from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TreatmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'treatments'
    verbose_name = _('Treatments')
    
    def ready(self):
        import treatments.signals  # noqa


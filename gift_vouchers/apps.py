from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GiftVouchersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gift_vouchers'
    verbose_name = _('Gift Vouchers')


from django.contrib import admin
from .models import GiftVoucher


@admin.register(GiftVoucher)
class GiftVoucherAdmin(admin.ModelAdmin):
    list_display = ['recipient_name', 'treatment', 'purchaser_email', 'email_option', 'is_sent', 'created_at']
    list_filter = []  # Filters disabled
    search_fields = ['recipient_name', 'purchaser_email', 'purchaser_first_name', 'purchaser_last_name']
    readonly_fields = ['created_at']


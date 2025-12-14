from django.contrib import admin
from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['user', 'treatment', 'date', 'start_time', 'end_time', 'status', 'created_at']
    list_filter = ['status', 'date', 'created_at']
    search_fields = ['user__username', 'user__email', 'treatment__title_hr', 'treatment__title_en']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'


from django.contrib import admin
from .models import ContactSubmission


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'mobile', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'mobile', 'message']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


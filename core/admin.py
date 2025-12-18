from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from .models import EmailCollection
import csv

# Unregister Groups from admin
admin.site.unregister(Group)


# Prevent superuser deletion
class UserAdmin(admin.ModelAdmin):
    def delete_model(self, request, obj):
        if obj.is_superuser:
            messages.error(request, _('Cannot delete superuser accounts.'))
            return
        super().delete_model(request, obj)
    
    def delete_queryset(self, request, queryset):
        superusers = queryset.filter(is_superuser=True)
        if superusers.exists():
            messages.error(request, _('Cannot delete superuser accounts.'))
            queryset = queryset.exclude(is_superuser=True)
        super().delete_queryset(request, queryset)


# Unregister default User admin and register custom one
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAdmin)


@admin.register(EmailCollection)
class EmailCollectionAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'mobile', 'source', 'created_at', 'user']
    list_filter = []  # Filters disabled
    search_fields = ['email', 'first_name', 'last_name', 'mobile', 'source']
    readonly_fields = ['created_at']
    
    actions = ['export_as_csv', 'export_as_text']
    
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="email_collection.csv"'
        writer = csv.writer(response)
        writer.writerow(['Email', 'First Name', 'Last Name', 'Mobile', 'Source', 'Created At', 'User'])
        for obj in queryset:
            writer.writerow([obj.email, obj.first_name, obj.last_name, obj.mobile, obj.source, obj.created_at, obj.user])
        return response
    export_as_csv.short_description = _("Export selected emails as CSV")
    
    def export_as_text(self, request, queryset):
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="email_collection.txt"'
        emails = '\n'.join([obj.email for obj in queryset])
        response.write(emails)
        return response
    export_as_text.short_description = _("Export selected emails as text (one per line)")


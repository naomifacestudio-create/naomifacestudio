from django.contrib import admin
from django.contrib.auth.models import Group
from django.http import HttpResponse
from .models import EmailCollection
import csv

# Unregister Groups from admin
admin.site.unregister(Group)


@admin.register(EmailCollection)
class EmailCollectionAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'mobile', 'source', 'created_at', 'user']
    list_filter = ['source', 'created_at']
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
    export_as_csv.short_description = "Export selected emails as CSV"
    
    def export_as_text(self, request, queryset):
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="email_collection.txt"'
        emails = '\n'.join([obj.email for obj in queryset])
        response.write(emails)
        return response
    export_as_text.short_description = "Export selected emails as text (one per line)"


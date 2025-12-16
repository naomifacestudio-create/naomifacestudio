from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.html import format_html
from django.utils import timezone
from datetime import datetime, date
from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['user', 'treatment', 'date', 'start_time', 'end_time', 'status', 'created_at']
    list_filter = ['status', 'date', 'created_at']
    search_fields = ['user__username', 'user__email', 'treatment__title_hr', 'treatment__title_en']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_calendar_link'] = True
        extra_context['calendar_url'] = 'admin:reservations_reservation_calendar'
        return super().changelist_view(request, extra_context=extra_context)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('calendar/', self.admin_site.admin_view(self.calendar_view), name='reservations_reservation_calendar'),
            path('calendar/day-reservations/', self.admin_site.admin_view(self.get_day_reservations), name='reservations_day_reservations'),
            path('calendar/month-reservations/', self.admin_site.admin_view(self.get_month_reservations), name='reservations_month_reservations'),
        ]
        return custom_urls + urls
    
    def calendar_view(self, request):
        """Admin calendar view"""
        context = {
            **self.admin_site.each_context(request),
            'title': 'Reservation Calendar',
            'opts': self.model._meta,
        }
        return render(request, 'admin/reservations/reservation_calendar.html', context)
    
    def get_day_reservations(self, request):
        """API endpoint to get reservations for a specific day"""
        selected_date = request.GET.get('date')
        if not selected_date:
            return JsonResponse({'error': 'Date parameter required'}, status=400)
        
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format'}, status=400)
        
        reservations = Reservation.objects.filter(date=selected_date).select_related('user', 'treatment').order_by('start_time')
        
        reservations_data = []
        for reservation in reservations:
            reservations_data.append({
                'id': reservation.id,
                'user': reservation.user.get_full_name() or reservation.user.username,
                'user_email': reservation.user.email,
                'treatment': reservation.treatment.get_title(),
                'start_time': reservation.start_time.strftime('%H:%M'),
                'end_time': reservation.end_time.strftime('%H:%M'),
                'status': reservation.get_status_display(),
                'notes': reservation.notes,
            })
        
        return JsonResponse({'reservations': reservations_data})
    
    def get_month_reservations(self, request):
        """API endpoint to get dates with reservations for a month"""
        year = request.GET.get('year')
        month = request.GET.get('month')
        
        if not year or not month:
            return JsonResponse({'error': 'Year and month parameters required'}, status=400)
        
        try:
            year = int(year)
            month = int(month)
            from calendar import monthrange
            _, last_day = monthrange(year, month)
            start_date = date(year, month, 1)
            end_date = date(year, month, last_day)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid year or month'}, status=400)
        
        # Get all dates that have reservations in this month
        reservations = Reservation.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).values_list('date', flat=True).distinct()
        
        dates_with_reservations = [date.isoformat() for date in reservations]
        
        return JsonResponse({'dates': dates_with_reservations})


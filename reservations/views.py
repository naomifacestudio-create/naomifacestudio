from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.translation import get_language
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from datetime import datetime, timedelta, date
from .models import Reservation
from treatments.models import Treatment
from core.models import EmailCollection
import json


def send_reservation_emails(reservation, language_code='hr'):
    """Send reservation confirmation emails to user and admin"""
    context = {
        'reservation': reservation,
        'treatment': reservation.treatment,
        'user': reservation.user,
        'language_code': language_code,
    }
    
    # User email
    user_subject = f'Reservation Confirmation - {reservation.treatment.get_title(language_code)}'
    user_message = render_to_string('reservations/emails/user_confirmation.html', context)
    send_mail(
        user_subject,
        user_message,
        settings.DEFAULT_FROM_EMAIL,
        [reservation.user.email],
        html_message=user_message,
        fail_silently=False,
    )
    
    # Admin email
    admin_subject = f'New Reservation - {reservation.treatment.get_title(language_code)}'
    admin_message = render_to_string('reservations/emails/admin_notification.html', context)
    send_mail(
        admin_subject,
        admin_message,
        settings.DEFAULT_FROM_EMAIL,
        [settings.ADMIN_EMAIL],
        html_message=admin_message,
        fail_silently=False,
    )


def send_cancellation_email(reservation, language_code='hr'):
    """Send cancellation email to admin"""
    context = {
        'reservation': reservation,
        'treatment': reservation.treatment,
        'user': reservation.user,
        'language_code': language_code,
    }
    
    admin_subject = f'Reservation Cancelled - {reservation.treatment.get_title(language_code)}'
    admin_message = render_to_string('reservations/emails/cancellation_notification.html', context)
    send_mail(
        admin_subject,
        admin_message,
        settings.DEFAULT_FROM_EMAIL,
        [settings.ADMIN_EMAIL],
        html_message=admin_message,
        fail_silently=False,
    )


def reservation_calendar(request, treatment_slug=None):
    """Reservation calendar view"""
    language_code = get_language()[:2]
    
    if treatment_slug:
        if language_code == 'en':
            treatment = get_object_or_404(Treatment, slug_en=treatment_slug, is_active=True)
        else:
            treatment = get_object_or_404(Treatment, slug_hr=treatment_slug, is_active=True)
    else:
        treatment = None
    
    treatments = Treatment.objects.filter(is_active=True)
    
    context = {
        'treatment': treatment,
        'treatments': treatments,
        'language_code': language_code,
    }
    return render(request, 'reservations/calendar.html', context)


@require_http_methods(["GET"])
def get_available_slots(request):
    """API endpoint to get available time slots for a date"""
    treatment_id = request.GET.get('treatment_id')
    selected_date = request.GET.get('date')
    
    if not treatment_id or not selected_date:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        treatment = Treatment.objects.get(id=treatment_id, is_active=True)
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except (Treatment.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Invalid treatment or date'}, status=400)
    
    # Get working hours for the day
    day_of_week = selected_date.weekday()
    working_hours = Reservation.get_working_hours(day_of_week)
    
    if not working_hours:
        return JsonResponse({'available_slots': []})
    
    # Get existing reservations for the date
    existing_reservations = Reservation.objects.filter(
        date=selected_date,
        status__in=['pending', 'confirmed']
    )
    
    # Generate time slots
    available_slots = []
    start_time = working_hours[0]
    end_time = working_hours[1]
    slot_duration = timedelta(minutes=15)  # 15-minute intervals
    treatment_duration = timedelta(minutes=treatment.get_total_minutes())
    
    current_time = datetime.combine(selected_date, start_time)
    end_datetime = datetime.combine(selected_date, end_time)
    
    while current_time + treatment_duration <= end_datetime:
        slot_start = current_time.time()
        slot_end = (current_time + treatment_duration).time()
        
        # Check if slot is available
        is_available = True
        for reservation in existing_reservations:
            res_start = datetime.combine(selected_date, reservation.start_time)
            res_end = datetime.combine(selected_date, reservation.end_time)
            
            # Check for overlap
            if not (current_time + treatment_duration <= res_start or current_time >= res_end):
                is_available = False
                break
        
        if is_available:
            available_slots.append({
                'start': slot_start.strftime('%H:%M'),
                'end': slot_end.strftime('%H:%M'),
            })
        
        current_time += slot_duration
    
    return JsonResponse({'available_slots': available_slots})


@login_required
@require_http_methods(["POST"])
def create_reservation(request):
    """Create a new reservation"""
    data = json.loads(request.body)
    
    treatment_id = data.get('treatment_id')
    reservation_date = data.get('date')
    start_time_str = data.get('start_time')
    
    if not all([treatment_id, reservation_date, start_time_str]):
        return JsonResponse({'error': 'Missing required fields'}, status=400)
    
    try:
        treatment = Treatment.objects.get(id=treatment_id, is_active=True)
        reservation_date = datetime.strptime(reservation_date, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
    except (Treatment.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Invalid data'}, status=400)
    
    # Check if slot is available
    if not Reservation.is_available(reservation_date, start_time, treatment):
        return JsonResponse({'error': 'Time slot is not available'}, status=400)
    
    # Create reservation
    reservation = Reservation.objects.create(
        user=request.user,
        treatment=treatment,
        date=reservation_date,
        start_time=start_time,
    )
    
    # Collect email
    EmailCollection.objects.get_or_create(
        email=request.user.email,
        defaults={'source': 'Reservation', 'user': request.user}
    )
    
    # Send email notifications
    send_reservation_emails(reservation, get_language()[:2])
    
    return JsonResponse({
        'success': True,
        'reservation_id': reservation.id,
        'message': 'Reservation created successfully'
    })


@login_required
def my_reservations(request):
    """View user's reservations"""
    reservations = Reservation.objects.filter(user=request.user).order_by('-date', '-start_time')
    
    context = {
        'reservations': reservations,
    }
    return render(request, 'reservations/my_reservations.html', context)


@login_required
@require_http_methods(["POST"])
def cancel_reservation(request, reservation_id):
    """Cancel a reservation"""
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    
    if reservation.status == 'cancelled':
        return JsonResponse({'error': 'Reservation already cancelled'}, status=400)
    
    reservation.status = 'cancelled'
    reservation.save()
    
    # Send cancellation email
    send_cancellation_email(reservation, get_language()[:2])
    
    return JsonResponse({'success': True, 'message': 'Reservation cancelled'})


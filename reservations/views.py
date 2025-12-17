from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.translation import get_language, activate, gettext as _
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from datetime import datetime, timedelta, date, time as dt_time
from .models import Reservation
from treatments.models import Treatment
from core.models import EmailCollection
import json
import logging

logger = logging.getLogger('reservations')


def send_reservation_emails(reservation, language_code='hr'):
    """Send reservation confirmation emails to user and admin"""
    # Activate the language for email rendering
    current_language = get_language()
    try:
        activate(language_code)
        
        # Get user profile for mobile phone
        profile = getattr(reservation.user, 'profile', None)
        
        # Get translated treatment title
        treatment_title = reservation.treatment.get_title(language_code)
        
        context = {
            'reservation': reservation,
            'treatment': reservation.treatment,
            'user': reservation.user,
            'user_profile': profile,
            'language_code': language_code,
            'treatment_title': treatment_title,
        }
        
        # User email - translate subject
        user_subject = _('Reservation Confirmation - %(treatment)s') % {'treatment': treatment_title}
        user_message = render_to_string('reservations/emails/user_confirmation.html', context)
        send_mail(
            user_subject,
            user_message,
            settings.DEFAULT_FROM_EMAIL,
            [reservation.user.email],
            html_message=user_message,
            fail_silently=False,
        )
        logger.info(f"Reservation confirmation email sent to user: {reservation.user.email} for reservation ID: {reservation.id}")
        
        # Admin email - translate subject
        admin_subject = _('New Reservation - %(treatment)s') % {'treatment': treatment_title}
        admin_message = render_to_string('reservations/emails/admin_notification.html', context)
        send_mail(
            admin_subject,
            admin_message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            html_message=admin_message,
            fail_silently=False,
        )
        logger.info(f"Reservation notification email sent to admin for reservation ID: {reservation.id}")
    except Exception as e:
        logger.error(f"Failed to send reservation emails for reservation ID: {reservation.id}. Error: {str(e)}", exc_info=True)
        raise
    finally:
        # Restore previous language
        activate(current_language)


def send_cancellation_email(reservation, language_code='hr'):
    """Send cancellation email to admin"""
    # Activate the language for email rendering
    current_language = get_language()
    try:
        activate(language_code)
        
        # Get user profile for mobile phone
        profile = getattr(reservation.user, 'profile', None)
        
        # Get translated treatment title
        treatment_title = reservation.treatment.get_title(language_code)
        
        context = {
            'reservation': reservation,
            'treatment': reservation.treatment,
            'user': reservation.user,
            'user_profile': profile,
            'language_code': language_code,
            'treatment_title': treatment_title,
        }
        
        # Translate subject
        admin_subject = _('Reservation Cancelled - %(treatment)s') % {'treatment': treatment_title}
        admin_message = render_to_string('reservations/emails/cancellation_notification.html', context)
        send_mail(
            admin_subject,
            admin_message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            html_message=admin_message,
            fail_silently=False,
        )
        logger.info(f"Cancellation email sent to admin for reservation ID: {reservation.id}")
    except Exception as e:
        logger.error(f"Failed to send cancellation email for reservation ID: {reservation.id}. Error: {str(e)}", exc_info=True)
        raise
    finally:
        # Restore previous language
        activate(current_language)


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
    
    # Get current date in Croatia timezone for calendar
    today_croatia = timezone.localtime(timezone.now()).date()
    
    context = {
        'treatment': treatment,
        'treatments': treatments,
        'language_code': language_code,
        'today_croatia': today_croatia.isoformat(),  # Pass as ISO format string
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
        # Day is closed (Saturday or Sunday)
        return JsonResponse({
            'available_slots': [],
            'reason': 'closed',
            'message': 'This day is closed (Saturday or Sunday)'
        })
    
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
    
    # Get current datetime in Croatia timezone (settings.TIME_ZONE = 'Europe/Zagreb')
    # timezone.localtime() converts UTC to the timezone set in settings.TIME_ZONE
    now_croatia = timezone.localtime(timezone.now())
    today_croatia = now_croatia.date()
    
    if selected_date == today_croatia:
        # If selecting today, start from current time in Croatia + 1 hour buffer
        now_time_croatia = now_croatia.replace(second=0, microsecond=0) + timedelta(hours=1)
        # Create timezone-aware datetime from current_time (assume Croatia timezone)
        # For comparison, we need both datetimes to be timezone-aware
        current_time_aware = timezone.make_aware(current_time)
        
        if current_time_aware < now_time_croatia:
            current_time_aware = now_time_croatia
            # Round up to next 15-minute interval
            minutes_to_add = 15 - (current_time_aware.minute % 15)
            if minutes_to_add < 15:
                current_time_aware += timedelta(minutes=minutes_to_add)
            # Convert back to naive datetime (in Croatia timezone) for the loop
            current_time = current_time_aware.astimezone(timezone.get_current_timezone()).replace(tzinfo=None)
    
    while current_time + treatment_duration <= end_datetime:
        slot_start = current_time.time()
        slot_end = (current_time + treatment_duration).time()
        
        # Skip if slot is in the past (for today) - compare in Croatia timezone
        if selected_date == today_croatia:
            current_time_aware = timezone.make_aware(current_time)
            if current_time_aware < now_croatia:
                current_time += slot_duration
                continue
        
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
    message = data.get('message', '').strip()
    
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
        notes=message,
    )
    
    # Collect email with user details (only if not already archived)
    profile = getattr(request.user, 'profile', None)
    EmailCollection.collect_email(
        email=request.user.email,
        source='Reservation',
        first_name=request.user.first_name or (profile.first_name if profile else ''),
        last_name=request.user.last_name or (profile.last_name if profile else ''),
        mobile=profile.mobile if profile else '',
        user=request.user,
        update_user_info=False,  # Don't update if email already exists
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


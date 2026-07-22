from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.translation import get_language, activate, gettext as _
from core.i18n_utils import active_django_language, active_language_code
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from datetime import datetime, timedelta, date, time as dt_time
from calendar import monthrange
from .models import Reservation, ReservationBlockedDate
from treatments.models import Treatment
from core.models import EmailCollection
import json
import logging

logger = logging.getLogger('reservations')


def send_reservation_emails(reservation, language_code='hr'):
    """Send reservation confirmation emails to user and admin"""
    # Activate the language for email rendering
    current_language = get_language()
    django_language = active_django_language(language_code)
    content_language = active_language_code(language_code)
    try:
        activate(django_language)
        
        # Get user profile for mobile phone
        profile = getattr(reservation.user, 'profile', None)
        
        # Get translated treatment title
        treatment_title = reservation.treatment.get_title(content_language)
        
        context = {
            'reservation': reservation,
            'treatment': reservation.treatment,
            'user': reservation.user,
            'user_profile': profile,
            'language_code': content_language,
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
    django_language = active_django_language(language_code)
    content_language = active_language_code(language_code)
    try:
        activate(django_language)
        
        # Get user profile for mobile phone
        profile = getattr(reservation.user, 'profile', None)
        
        # Get translated treatment title
        treatment_title = reservation.treatment.get_title(content_language)
        
        context = {
            'reservation': reservation,
            'treatment': reservation.treatment,
            'user': reservation.user,
            'user_profile': profile,
            'language_code': content_language,
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
        qs = Treatment.objects.publicly_visible()
        if language_code == 'en':
            treatment = get_object_or_404(qs, slug_en=treatment_slug)
        else:
            treatment = get_object_or_404(qs, slug_hr=treatment_slug)
    else:
        treatment = None
    
    treatments = Treatment.objects.publicly_visible()
    
    # Get current date in local timezone for calendar
    today_local = timezone.localtime(timezone.now()).date()
    
    context = {
        'treatment': treatment,
        'treatments': treatments,
        'language_code': language_code,
        'today_local': today_local.isoformat(),  # Pass as ISO format string
    }
    return render(request, 'reservations/calendar.html', context)


@require_http_methods(["GET"])
def get_blocked_dates(request):
    """API endpoint to get blocked reservation dates in a month."""
    year = request.GET.get('year')
    month = request.GET.get('month')
    if not year or not month:
        return JsonResponse({'error': 'Year and month parameters required'}, status=400)

    try:
        year = int(year)
        month = int(month)
        _, last_day = monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, last_day)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid year or month'}, status=400)

    blocked = ReservationBlockedDate.objects.filter(
        is_active=True,
        date__gte=start_date,
        date__lte=end_date,
    ).values('date', 'reason')

    return JsonResponse({
        'blocked_dates': [
            {'date': item['date'].isoformat(), 'reason': item['reason']}
            for item in blocked
        ]
    })


@require_http_methods(["GET"])
def get_available_slots(request):
    """API endpoint to get available time slots for a date"""
    treatment_id = request.GET.get('treatment_id')
    selected_date = request.GET.get('date')
    
    if not treatment_id or not selected_date:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        treatment = Treatment.objects.publicly_visible().get(id=treatment_id)
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except (Treatment.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Invalid treatment or date'}, status=400)
    
    blocked_day = ReservationBlockedDate.get_block_for_date(selected_date)
    if blocked_day:
        return JsonResponse({
            'available_slots': [],
            'reason': 'blocked',
            'message': blocked_day.reason or 'Reservations are disabled for this date'
        })

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
    
    # Get current datetime in local timezone (settings.TIME_ZONE = 'Europe/Zagreb')
    # timezone.localtime() converts UTC to the timezone set in settings.TIME_ZONE
    now_local = timezone.localtime(timezone.now())
    today_local = now_local.date()
    
    if selected_date == today_local:
        # If selecting today, start from current time in Croatia + 1 hour buffer
        now_time_local = now_local.replace(second=0, microsecond=0) + timedelta(hours=1)
        # Create timezone-aware datetime from current_time (assume local timezone)
        # For comparison, we need both datetimes to be timezone-aware
        current_time_aware = timezone.make_aware(current_time)
        
        if current_time_aware < now_time_local:
            current_time_aware = now_time_local
            # Round up to next 15-minute interval
            minutes_to_add = 15 - (current_time_aware.minute % 15)
            if minutes_to_add < 15:
                current_time_aware += timedelta(minutes=minutes_to_add)
            # Convert back to naive datetime (in local timezone) for the loop
            current_time = current_time_aware.astimezone(timezone.get_current_timezone()).replace(tzinfo=None)
    
    while current_time + treatment_duration <= end_datetime:
        slot_start = current_time.time()
        slot_end = (current_time + treatment_duration).time()
        
        # Skip if slot is in the past (for today) - compare in local timezone
        if selected_date == today_local:
            current_time_aware = timezone.make_aware(current_time)
            if current_time_aware < now_local:
                current_time += slot_duration
                continue
        
        # Check if slot is available
        is_available = True
        for reservation in existing_reservations:
            res_start = datetime.combine(selected_date, reservation.start_time)
            res_end = datetime.combine(selected_date, reservation.end_time)
            # Add pause period after reservation
            pause_minutes = reservation.treatment.get_total_pause_minutes()
            res_end_with_pause = res_end + timedelta(minutes=pause_minutes)
            
            # Check for overlap (including pause period)
            # Slot is available if it starts after reservation+pause ends OR ends before reservation starts
            if not (current_time >= res_end_with_pause or current_time + treatment_duration <= res_start):
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
        treatment = Treatment.objects.publicly_visible().get(id=treatment_id)
        reservation_date = datetime.strptime(reservation_date, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
    except (Treatment.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    blocked_day = ReservationBlockedDate.get_block_for_date(reservation_date)
    if blocked_day:
        return JsonResponse(
            {'error': blocked_day.reason or 'Reservations are disabled for this date'},
            status=400
        )
    
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


from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from treatments.models import Treatment
from django.core.validators import MinValueValidator
from datetime import datetime, time, timedelta


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('confirmed', _('Confirmed')),
        ('cancelled', _('Cancelled')),
        ('completed', _('Completed')),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    treatment = models.ForeignKey(Treatment, on_delete=models.CASCADE, related_name='reservations')
    date = models.DateField(_('Date'))
    start_time = models.TimeField(_('Start Time'))
    end_time = models.TimeField(_('End Time'))
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='confirmed')
    notes = models.TextField(_('Notes'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date', 'start_time']
        verbose_name = _('Reservation')
        verbose_name_plural = _('Reservations')
        unique_together = [['date', 'start_time']]
    
    def __str__(self):
        return f"{self.user.username} - {self.treatment.title_hr} - {self.date} {self.start_time}"
    
    def save(self, *args, **kwargs):
        """Calculate end_time based on treatment duration"""
        if not self.end_time:
            start_datetime = datetime.combine(self.date, self.start_time)
            duration_minutes = self.treatment.get_total_minutes()
            end_datetime = start_datetime + timedelta(minutes=duration_minutes)
            self.end_time = end_datetime.time()
        super().save(*args, **kwargs)
    
    @staticmethod
    def get_working_hours(day_of_week):
        """Get working hours for a specific day (0=Monday, 6=Sunday)"""
        working_hours = {
            0: (time(12, 0), time(20, 0)),  # Monday
            1: (time(9, 0), time(17, 0)),   # Tuesday
            2: (time(9, 0), time(17, 0)),   # Wednesday
            3: (time(12, 0), time(20, 0)),  # Thursday
            4: (time(9, 0), time(17, 0)),   # Friday
            5: None,  # Saturday - Closed
            6: None,  # Sunday - Closed
        }
        return working_hours.get(day_of_week)
    
    @staticmethod
    def is_available(date, start_time, treatment, exclude_reservation=None):
        """Check if a time slot is available"""
        # Check if day is working day
        day_of_week = date.weekday()
        working_hours = Reservation.get_working_hours(day_of_week)
        if not working_hours:
            return False
        
        # Check if start_time is within working hours
        if start_time < working_hours[0] or start_time >= working_hours[1]:
            return False
        
        # Calculate end_time
        start_datetime = datetime.combine(date, start_time)
        duration_minutes = treatment.get_total_minutes()
        end_datetime = start_datetime + timedelta(minutes=duration_minutes)
        end_time = end_datetime.time()
        
        # Check if end_time is within working hours
        if end_time > working_hours[1]:
            return False
        
        # Check for overlapping reservations
        overlapping = Reservation.objects.filter(
            date=date,
            status__in=['pending', 'confirmed'],
        ).exclude(
            id=exclude_reservation.id if exclude_reservation else None
        ).filter(
            models.Q(start_time__lt=end_time, end_time__gt=start_time)
        )
        
        return not overlapping.exists()


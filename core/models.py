from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class UserProfile(models.Model):
    """Extended user profile with additional information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    mobile = models.CharField(max_length=20, blank=True, help_text="Mobile phone number")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user.email})"
    
    @property
    def full_name(self):
        """Get full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.user.username


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create user profile when user is created"""
    if created:
        UserProfile.objects.create(user=instance)


class EmailCollection(models.Model):
    """Store all emails collected from contact forms and user registrations"""
    email = models.EmailField(unique=True)
    source = models.CharField(max_length=100, help_text="Where this email was collected from")
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Email Collection')
        verbose_name_plural = _('Email Collections')
    
    def __str__(self):
        return self.email
    
    @staticmethod
    def collect_email(email, source, first_name='', last_name='', mobile='', user=None, update_user_info=False):
        """
        Helper method to collect emails without creating duplicates.
        
        Args:
            email: Email address to collect
            source: Source of the email (e.g., 'Contact Form', 'User Registration')
            first_name: First name (optional)
            last_name: Last name (optional)
            mobile: Mobile number (optional)
            user: User object (optional, for registered users)
            update_user_info: If True and email exists, update user info (for User Registration)
        
        Returns:
            EmailCollection instance
        """
        if not email:
            return None
        
        # Check if email already exists
        existing = EmailCollection.objects.filter(email=email).first()
        
        if existing:
            # Email already exists - only update if update_user_info is True (for User Registration)
            if update_user_info:
                # Update user information if provided
                update_fields = {}
                if user:
                    update_fields['user'] = user
                if first_name:
                    update_fields['first_name'] = first_name
                if last_name:
                    update_fields['last_name'] = last_name
                if mobile:
                    update_fields['mobile'] = mobile
                
                if update_fields:
                    # Update only the fields that were provided
                    for field, value in update_fields.items():
                        setattr(existing, field, value)
                    existing.save(update_fields=list(update_fields.keys()))
            
            return existing
        else:
            # Email doesn't exist - create new entry
            return EmailCollection.objects.create(
                email=email,
                source=source,
                first_name=first_name or '',
                last_name=last_name or '',
                mobile=mobile or '',
                user=user,
            )


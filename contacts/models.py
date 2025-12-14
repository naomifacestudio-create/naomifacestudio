from django.db import models
from django.utils.translation import gettext_lazy as _


class ContactSubmission(models.Model):
    first_name = models.CharField(_('First Name'), max_length=100)
    last_name = models.CharField(_('Last Name'), max_length=100)
    mobile = models.CharField(_('Mobile Number'), max_length=20)
    email = models.EmailField(_('Email Address'))
    message = models.TextField(_('Message'))
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(_('Read'), default=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Contact Submission')
        verbose_name_plural = _('Contact Submissions')
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"


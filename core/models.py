from django.db import models
from django.contrib.auth.models import User


class EmailCollection(models.Model):
    """Store all emails collected from contact forms and user registrations"""
    email = models.EmailField(unique=True)
    source = models.CharField(max_length=100, help_text="Where this email was collected from")
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email Collection'
        verbose_name_plural = 'Email Collections'
    
    def __str__(self):
        return self.email


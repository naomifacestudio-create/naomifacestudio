from django.db import models
from django.utils.translation import gettext_lazy as _
from treatments.models import Treatment


class GiftVoucher(models.Model):
    EMAIL_OPTION_CHOICES = [
        ('purchaser', _('Send the gift voucher to my email address')),
        ('recipient', _('Send the gift voucher to recipient\'s email address')),
    ]
    
    # Treatment selection
    treatment = models.ForeignKey(Treatment, on_delete=models.CASCADE, related_name='gift_vouchers')
    
    # Email delivery option
    email_option = models.CharField(_('Email Delivery Option'), max_length=20, choices=EMAIL_OPTION_CHOICES)
    
    # Gift voucher details
    recipient_name = models.CharField(_('Recipient Name'), max_length=200)
    personalised_message = models.TextField(_('Personalised Message'), blank=True)
    from_name = models.CharField(_('Who is this gift from?'), max_length=200)
    
    # Purchaser details
    purchaser_first_name = models.CharField(_('First Name'), max_length=100)
    purchaser_last_name = models.CharField(_('Last Name'), max_length=100)
    purchaser_email = models.EmailField(_('Email Address'))
    purchaser_mobile = models.CharField(_('Mobile Number'), max_length=20)
    
    # Recipient email (if different from purchaser)
    recipient_email = models.EmailField(_('Recipient Email Address'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(_('Email Sent'), default=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Gift Voucher')
        verbose_name_plural = _('Gift Vouchers')
    
    def __str__(self):
        return f"Gift Voucher for {self.recipient_name} - {self.treatment.title_hr}"
    
    def get_delivery_email(self):
        """Get the email address where voucher should be sent"""
        if self.email_option == 'recipient' and self.recipient_email:
            return self.recipient_email
        return self.purchaser_email


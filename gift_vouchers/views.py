from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import get_language
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from honeypot.decorators import check_honeypot
from django_ratelimit.decorators import ratelimit
from .models import GiftVoucher
from treatments.models import Treatment
from core.models import EmailCollection


@ratelimit(key='ip', rate='5/m', method='POST')
@check_honeypot
def gift_voucher_form(request):
    """Gift voucher form view"""
    language_code = get_language()[:2]
    treatments = Treatment.objects.filter(is_active=True)
    
    if request.method == 'POST':
        was_limited = getattr(request, 'limited', False)
        if was_limited:
            messages.error(request, 'Too many requests. Please try again later.')
            return redirect('gift_vouchers:form')
        
        treatment_id = request.POST.get('treatment')
        email_option = request.POST.get('email_option')
        recipient_name = request.POST.get('recipient_name')
        personalised_message = request.POST.get('personalised_message', '')
        from_name = request.POST.get('from_name')
        purchaser_first_name = request.POST.get('purchaser_first_name')
        purchaser_last_name = request.POST.get('purchaser_last_name')
        purchaser_email = request.POST.get('purchaser_email')
        purchaser_mobile = request.POST.get('purchaser_mobile')
        recipient_email = request.POST.get('recipient_email', '')
        
        # Validation
        if not all([treatment_id, email_option, recipient_name, from_name, 
                   purchaser_first_name, purchaser_last_name, purchaser_email, purchaser_mobile]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'gift_vouchers/form.html', {
                'treatments': treatments,
                'language_code': language_code,
            })
        
        try:
            treatment = Treatment.objects.get(id=treatment_id, is_active=True)
        except Treatment.DoesNotExist:
            messages.error(request, 'Invalid treatment selected.')
            return render(request, 'gift_vouchers/form.html', {
                'treatments': treatments,
                'language_code': language_code,
            })
        
        # Create gift voucher
        gift_voucher = GiftVoucher.objects.create(
            treatment=treatment,
            email_option=email_option,
            recipient_name=recipient_name,
            personalised_message=personalised_message,
            from_name=from_name,
            purchaser_first_name=purchaser_first_name,
            purchaser_last_name=purchaser_last_name,
            purchaser_email=purchaser_email,
            purchaser_mobile=purchaser_mobile,
            recipient_email=recipient_email if email_option == 'recipient' else '',
        )
        
        # Collect email
        EmailCollection.objects.get_or_create(
            email=purchaser_email,
            defaults={'source': 'Gift Voucher Form'}
        )
        
        # Send emails
        send_gift_voucher_emails(gift_voucher, language_code)
        
        messages.success(request, 'Gift voucher order submitted successfully!')
        return redirect('gift_vouchers:form')
    
    context = {
        'treatments': treatments,
        'language_code': language_code,
    }
    return render(request, 'gift_vouchers/form.html', context)


def send_gift_voucher_emails(gift_voucher, language_code='hr'):
    """Send gift voucher emails to purchaser, recipient, and admin"""
    # Email to purchaser/admin
    context = {
        'gift_voucher': gift_voucher,
        'language_code': language_code,
    }
    
    # Admin email
    admin_subject = f'New Gift Voucher Order - {gift_voucher.recipient_name}'
    admin_message = render_to_string('gift_vouchers/emails/admin_notification.html', context)
    send_mail(
        admin_subject,
        admin_message,
        settings.DEFAULT_FROM_EMAIL,
        [settings.ADMIN_EMAIL],
        html_message=admin_message,
        fail_silently=False,
    )
    
    # Purchaser email
    purchaser_subject = f'Gift Voucher Order Confirmation - {gift_voucher.treatment.get_title(language_code)}'
    purchaser_message = render_to_string('gift_vouchers/emails/purchaser_confirmation.html', context)
    send_mail(
        purchaser_subject,
        purchaser_message,
        settings.DEFAULT_FROM_EMAIL,
        [gift_voucher.purchaser_email],
        html_message=purchaser_message,
        fail_silently=False,
    )
    
    # Recipient email (if different)
    if gift_voucher.email_option == 'recipient' and gift_voucher.recipient_email:
        recipient_subject = f'You received a Gift Voucher! - {gift_voucher.treatment.get_title(language_code)}'
        recipient_message = render_to_string('gift_vouchers/emails/recipient_notification.html', context)
        send_mail(
            recipient_subject,
            recipient_message,
            settings.DEFAULT_FROM_EMAIL,
            [gift_voucher.recipient_email],
            html_message=recipient_message,
            fail_silently=False,
        )
    
    gift_voucher.is_sent = True
    gift_voucher.save()


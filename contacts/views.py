from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import get_language, activate
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from honeypot.decorators import check_honeypot
from django_ratelimit.decorators import ratelimit
from .models import ContactSubmission
from core.models import EmailCollection
import logging

logger = logging.getLogger('contacts')


@ratelimit(key='ip', rate='5/m', method='POST')
@check_honeypot
def contact_form(request):
    """Contact form view"""
    language_code = get_language()[:2]
    
    if request.method == 'POST':
        was_limited = getattr(request, 'limited', False)
        if was_limited:
            messages.error(request, 'Too many requests. Please try again later.')
            return redirect('contacts:form')
        
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        mobile = request.POST.get('mobile')
        email = request.POST.get('email')
        message_text = request.POST.get('message')
        
        if not all([first_name, last_name, mobile, email, message_text]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'contacts/form.html', {'language_code': language_code})
        
        # Create contact submission
        submission = ContactSubmission.objects.create(
            first_name=first_name,
            last_name=last_name,
            mobile=mobile,
            email=email,
            message=message_text,
        )
        
        # Collect email (only if not already archived)
        EmailCollection.collect_email(
            email=email,
            source='Contact Form',
            first_name=first_name,
            last_name=last_name,
            mobile=mobile,
        )
        
        # Send email to admin
        send_contact_email(submission, language_code)
        
        messages.success(request, 'Thank you for your message! We will get back to you soon.')
        return redirect('contacts:form')
    
    context = {
        'language_code': language_code,
    }
    return render(request, 'contacts/form.html', context)


def send_contact_email(submission, language_code='hr'):
    """Send contact form email to admin"""
    # Activate the language for email rendering
    current_language = get_language()
    try:
        activate(language_code)
        
        context = {
            'submission': submission,
            'language_code': language_code,
        }
        
        subject = f'New Contact Form Submission from {submission.first_name} {submission.last_name}'
        message = render_to_string('contacts/emails/admin_notification.html', context)
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            html_message=message,
            fail_silently=False,
        )
        logger.info(f"Contact form email sent to admin for submission ID: {submission.id} from {submission.email}")
    except Exception as e:
        logger.error(f"Failed to send contact form email for submission ID: {submission.id}. Error: {str(e)}", exc_info=True)
        raise
    finally:
        # Restore previous language
        activate(current_language)


from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import get_language, gettext_lazy as _
from django.views.decorators.http import require_http_methods
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .models import EmailCollection
from reservations.models import Reservation


def home(request):
    """Home page view"""
    context = {
        'page_title': _('Home'),
    }
    return render(request, 'core/home.html', context)


def about_us(request):
    """About Us page view"""
    context = {
        'page_title': _('About Us'),
    }
    return render(request, 'core/about_us.html', context)


def signup_view(request):
    """User signup view"""
    language_code = get_language()[:2]
    
    if request.user.is_authenticated:
        return redirect('reservations:calendar')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Collect email with user details (update if exists, as this has the most complete info)
            profile = getattr(user, 'profile', None)
            EmailCollection.collect_email(
                email=user.email,
                source='User Registration',
                first_name=user.first_name,
                last_name=user.last_name,
                mobile=profile.mobile if profile else '',
                user=user,
                update_user_info=True,  # Update if email already exists from contact form
            )
            
            # Log the user in
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                messages.success(request, _('Account created successfully!'))
                next_url = request.GET.get('next', 'reservations:calendar')
                return redirect(next_url)
    else:
        form = CustomUserCreationForm()
    
    context = {
        'form': form,
        'language_code': language_code,
    }
    return render(request, 'core/signup.html', context)


def login_view(request):
    """User login view"""
    language_code = get_language()[:2]
    
    if request.user.is_authenticated:
        return redirect('reservations:calendar')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, _('Welcome back!'))
                next_url = request.GET.get('next', 'reservations:calendar')
                return redirect(next_url)
            else:
                messages.error(request, _('Invalid username or password.'))
    else:
        form = CustomAuthenticationForm()
    
    context = {
        'form': form,
        'language_code': language_code,
    }
    return render(request, 'core/login.html', context)


@login_required
def account_view(request):
    """User account page showing profile and reservations"""
    user = request.user
    profile = getattr(user, 'profile', None)
    
    # Get past and future reservations
    from django.utils import timezone
    today = timezone.now().date()
    
    future_reservations = Reservation.objects.filter(
        user=user,
        date__gte=today
    ).order_by('date', 'start_time')
    
    past_reservations = Reservation.objects.filter(
        user=user,
        date__lt=today
    ).order_by('-date', '-start_time')[:10]  # Show last 10 past reservations
    
    context = {
        'user': user,
        'profile': profile,
        'future_reservations': future_reservations,
        'past_reservations': past_reservations,
    }
    return render(request, 'core/account.html', context)


from django.shortcuts import render
from django.utils.translation import gettext_lazy as _


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


from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.utils.translation import get_language
from django.db.models import Q
from .models import Treatment


def treatment_list(request):
    """List all treatments with pagination"""
    language_code = get_language()[:2]
    treatments = Treatment.objects.filter(is_active=True).order_by('-created_at')
    
    paginator = Paginator(treatments, 4)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'treatments': page_obj,
        'language_code': language_code,
    }
    return render(request, 'treatments/list.html', context)


def treatment_detail(request, slug):
    """Individual treatment detail page"""
    language_code = get_language()[:2]
    
    # Try to find treatment by slug in current language
    if language_code == 'en':
        treatment = get_object_or_404(Treatment, slug_en=slug, is_active=True)
    else:
        treatment = get_object_or_404(Treatment, slug_hr=slug, is_active=True)
    
    context = {
        'treatment': treatment,
        'language_code': language_code,
    }
    return render(request, 'treatments/detail.html', context)


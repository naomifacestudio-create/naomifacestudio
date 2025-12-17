from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.utils.translation import get_language
from .models import Education


def education_list(request):
    """List all education items with pagination"""
    language_code = get_language()[:2]
    education_items = Education.objects.filter(is_active=True).order_by('-created_at')
    
    paginator = Paginator(education_items, 6)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'education_items': page_obj,
        'language_code': language_code,
    }
    return render(request, 'education/list.html', context)


def education_detail(request, slug):
    """Individual education detail page"""
    language_code = get_language()[:2]
    
    if language_code == 'en':
        education = get_object_or_404(Education, slug_en=slug, is_active=True)
    else:
        education = get_object_or_404(Education, slug_hr=slug, is_active=True)
    
    context = {
        'education': education,
        'language_code': language_code,
    }
    return render(request, 'education/detail.html', context)



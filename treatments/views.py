from django.shortcuts import render, get_object_or_404
from django.utils.translation import get_language
from .models import Treatment


def treatment_list(request):
    """List all active treatments on one page with optional price sorting"""
    language_code = get_language()[:2]
    sort = request.GET.get('sort', '')
    if sort not in ('', 'price_asc', 'price_desc'):
        sort = ''

    qs = Treatment.objects.filter(is_active=True)
    if sort == 'price_asc':
        qs = qs.order_by('price', '-created_at')
    elif sort == 'price_desc':
        qs = qs.order_by('-price', '-created_at')
    else:
        qs = qs.order_by('-created_at')

    context = {
        'treatments': qs,
        'language_code': language_code,
        'current_sort': sort,
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


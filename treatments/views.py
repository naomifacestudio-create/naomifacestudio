from django.shortcuts import render, get_object_or_404

from core.i18n_utils import active_language_code
from .models import Treatment


def treatment_list(request):
    """List all active treatments on one page with optional price sorting"""
    language_code = active_language_code()
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
    language_code = active_language_code()
    preview = request.GET.get('preview') == '1' and request.user.is_staff
    queryset = Treatment.objects.all() if preview else Treatment.objects.filter(is_active=True)

    # Try to find treatment by slug in current language
    if language_code == 'en':
        treatment = get_object_or_404(queryset, slug_en=slug)
    else:
        treatment = get_object_or_404(queryset, slug_sr=slug)
    
    context = {
        'treatment': treatment,
        'language_code': language_code,
        'is_admin_preview': preview,
        'seo': treatment.get_seo_context(request),
    }
    return render(request, 'treatments/detail.html', context)


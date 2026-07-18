from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import Http404
from core.i18n_utils import active_language_code
from .models import Education


def education_list(request):
    """List all education items with pagination"""
    language_code = active_language_code()
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
    language_code = active_language_code()
    preview = request.GET.get('preview') == '1' and request.user.is_staff

    qs = Education.objects.all() if preview else Education.objects.filter(is_active=True)
    if language_code == 'en':
        education = get_object_or_404(qs, slug_en=slug)
    else:
        education = get_object_or_404(qs, slug_hr=slug)

    if not preview and not education.is_active:
        raise Http404

    context = {
        'education': education,
        'language_code': language_code,
        'is_admin_preview': preview,
        'seo': education.get_seo_context(request),
    }
    return render(request, 'education/detail.html', context)

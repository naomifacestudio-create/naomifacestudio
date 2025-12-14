from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.utils.translation import get_language
from .models import Blog


def blog_list(request):
    """List all blogs with pagination"""
    language_code = get_language()[:2]
    blogs = Blog.objects.filter(is_active=True).order_by('-created_at')
    
    paginator = Paginator(blogs, 6)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'blogs': page_obj,
        'language_code': language_code,
    }
    return render(request, 'blogs/list.html', context)


def blog_detail(request, slug):
    """Individual blog detail page"""
    language_code = get_language()[:2]
    
    if language_code == 'en':
        blog = get_object_or_404(Blog, slug_en=slug, is_active=True)
    else:
        blog = get_object_or_404(Blog, slug_hr=slug, is_active=True)
    
    context = {
        'blog': blog,
        'language_code': language_code,
    }
    return render(request, 'blogs/detail.html', context)


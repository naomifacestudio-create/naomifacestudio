from django.urls import path
from . import views

app_name = 'education'

urlpatterns = [
    path('', views.education_list, name='list'),
    path('<slug:slug>/', views.education_detail, name='detail'),
]



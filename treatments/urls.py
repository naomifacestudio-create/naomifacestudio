from django.urls import path
from . import views

app_name = 'treatments'

urlpatterns = [
    path('', views.treatment_list, name='list'),
    path('<slug:slug>/', views.treatment_detail, name='detail'),
]


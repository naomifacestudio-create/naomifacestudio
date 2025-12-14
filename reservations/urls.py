from django.urls import path
from . import views

app_name = 'reservations'

urlpatterns = [
    path('', views.reservation_calendar, name='calendar'),
    path('treatment/<slug:treatment_slug>/', views.reservation_calendar, name='calendar_with_treatment'),
    path('api/available-slots/', views.get_available_slots, name='available_slots'),
    path('api/create/', views.create_reservation, name='create'),
    path('my-reservations/', views.my_reservations, name='my_reservations'),
    path('cancel/<int:reservation_id>/', views.cancel_reservation, name='cancel'),
]


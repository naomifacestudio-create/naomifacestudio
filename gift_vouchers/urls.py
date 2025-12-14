from django.urls import path
from . import views

app_name = 'gift_vouchers'

urlpatterns = [
    path('', views.gift_voucher_form, name='form'),
]


from django.urls import path
from . import views

urlpatterns = [
    path("devices/", views.list_devices),
    path("headphones/brands/", views.list_brands),
    path("headphones/", views.list_headphones),
]

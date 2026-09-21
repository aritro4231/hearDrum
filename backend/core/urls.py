from django.urls import path
from . import views

urlpatterns = [
    path("auth/register/", views.register),
    path("auth/login/", views.login),
    path("auth/logout/", views.logout),
    path("devices/", views.list_devices),
    path("headphones/brands/", views.list_brands),
    path("headphones/", views.list_headphones),
    path("sessions/", views.listening_sessions),
]

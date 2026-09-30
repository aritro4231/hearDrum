from django.urls import path
from . import views

urlpatterns = [
    path("auth/register/", views.register),
    path("auth/login/", views.login),
    path("auth/logout/", views.logout),
    path("devices/", views.list_devices),
    path("headphones/brands/", views.list_brands),
    path("headphones/", views.list_headphones),
    path("ambient/analyze/", views.analyze_ambient),
    path("sessions/current/", views.current_listening_session),
    path("sessions/today/", views.today_listening_summary),
    path("sessions/start/", views.start_listening_session),
    path("sessions/<int:session_id>/pause/", views.pause_listening_session),
    path("sessions/<int:session_id>/resume/", views.resume_listening_session),
    path("sessions/<int:session_id>/end/", views.end_listening_session),
    path("sessions/<int:session_id>/edit/", views.edit_listening_session_settings),
    path("sessions/", views.listening_sessions),
]

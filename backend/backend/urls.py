from django.contrib import admin
from django.urls import path, include
from core import views 
from core.views import health


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
]


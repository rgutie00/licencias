"""
urls.py — Servidor Central de Licencias
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Panel de administración
    path("admin/", admin.site.urls),

    # API de licencias v1
    path("api/v1/", include("licenses.urls")),
]

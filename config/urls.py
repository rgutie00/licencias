"""
config/urls.py — URLconf raíz del Servidor Central de Licencias.

    /admin/        → Panel de administración (Unfold)
    /api/v1/...    → API REST de licencias (licenses.urls)
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("licenses.urls")),
]

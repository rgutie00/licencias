"""
urls.py — Rutas del módulo de licencias.
Se incluye desde el proyecto Django con:
    path("license/", include("license_system.urls"))
"""
from django.urls import path

from . import views

urlpatterns = [
    path("activate/", views.activate, name="license-activate"),
    path("expired/", views.expired, name="license-expired"),
    path("success/", views.success, name="license-success"),
]

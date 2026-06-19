"""
urls.py — Rutas de la API de licencias.
Prefijo: /api/v1/ (definido en config/urls.py)
"""
from django.urls import path

from .views import ActivateLicenseView, TrialLicenseView, ValidateLicenseView

urlpatterns = [
    path("licenses/activate", ActivateLicenseView.as_view(), name="license-activate"),
    path("licenses/validate", ValidateLicenseView.as_view(), name="license-validate"),
    path("licenses/trial",    TrialLicenseView.as_view(),    name="license-trial"),
]

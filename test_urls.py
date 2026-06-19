"""
test_urls.py — URLs mínimas para los tests de Fase 2.
Simula el urls.py de un proyecto Django real que incluye license_system.
"""
from django.urls import include, path


def dummy_view(request):
    from django.http import HttpResponse
    # Expone info de licencia para verificar en tests
    if hasattr(request, "license"):
        return HttpResponse(f"OK license={request.license.status}", status=200)
    return HttpResponse("OK no-license-attr", status=200)


def login_view(request):
    from django.http import HttpResponse
    return HttpResponse("LOGIN PAGE", status=200)


urlpatterns = [
    path("license/", include("license_system.urls")),
    path("accounts/login/", login_view, name="login"),
    path("dashboard/", dummy_view, name="dashboard"),
    path("api/data/", dummy_view, name="api-data"),
]

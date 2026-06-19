"""
test_urls.py — URLs para tests de Fase 2 y Fase 3.
"""
from django.contrib import admin
from django.urls import include, path


def dummy_view(request):
    from django.http import HttpResponse
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
    path("admin/", admin.site.urls),
    path("api/v1/", include("licenses.urls")),
]

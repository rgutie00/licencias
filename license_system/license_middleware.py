"""
license_middleware.py — Middleware Django que valida la licencia
en cada request, salvo las rutas declaradas exentas en settings.
"""
from django.conf import settings
from django.http import HttpResponseRedirect

from .engine_factory import get_engine

DEFAULT_EXEMPT_URLS = [
    "/license/",
    "/static/",
    "/media/",
    "/favicon.ico",
]


class LicenseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        exempt_urls = getattr(settings, "LICENSE_EXEMPT_URLS", DEFAULT_EXEMPT_URLS)
        for exempt in exempt_urls:
            if path.startswith(exempt):
                return self.get_response(request)

        engine = get_engine()
        result = engine.validate()

        if result.status == "VALID":
            request.license = result
            if result.days_remaining is not None and result.days_remaining <= 7:
                request.license_warning = (
                    f"Su licencia vence en {result.days_remaining} días. "
                    "Renueve antes del vencimiento para evitar interrupciones."
                )
            return self.get_response(request)

        if result.status == "EXPIRED":
            return HttpResponseRedirect("/license/expired/")

        if result.status == "TAMPERED":
            engine.delete_token()
            return HttpResponseRedirect("/license/activate/?reason=tampered")

        if result.status == "CLOCK_ROLLBACK":
            engine.delete_token()
            return HttpResponseRedirect("/license/activate/?reason=clock")

        return HttpResponseRedirect("/license/activate/")

    @staticmethod
    def _get_ip(request) -> str:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            first = xff.split(",")[0].strip()
            if first:
                return first
        remote = request.META.get("REMOTE_ADDR")
        return remote if remote else "unknown"

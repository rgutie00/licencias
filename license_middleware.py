"""
license_middleware.py — Fase 2
Intercepta TODOS los requests de Django antes del login.

Posición OBLIGATORIA en settings.py:
    MIDDLEWARE = [
        'license_system.license_middleware.LicenseMiddleware',  # ← PRIMERO
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        ...
        'django.contrib.auth.middleware.AuthenticationMiddleware',
    ]

Flujo:
    Request → ¿ruta exenta? → SÍ → pasar directamente
                             → NO → validar licencia
                                      VALID        → request.license = result → continuar
                                      NO_LICENSE   → redirect /license/activate/
                                      TAMPERED     → borrar token → redirect /license/activate/?reason=tampered
                                      EXPIRED      → redirect /license/expired/
                                      CLOCK_ROLLBACK → borrar token → redirect /license/activate/?reason=clock
"""

import logging

from django.conf import settings
from django.shortcuts import redirect

from .engine_factory import get_engine

logger = logging.getLogger("license")


class LicenseMiddleware:
    """
    Middleware de validación de licencias.

    Se instancia una sola vez al arrancar Django.
    El LicenseEngine también se instancia una vez (singleton via engine_factory).
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # Rutas que NO requieren licencia activa
        raw_exempt = getattr(settings, "LICENSE_EXEMPT_URLS", [
            "/license/",
            "/static/",
            "/media/",
            "/favicon.ico",
            "/robots.txt",
        ])
        # Convertir a tupla para startswith() eficiente
        self.exempt = tuple(raw_exempt)

    def __call__(self, request):
        # ── 1. Rutas exentas — pasar sin validar ────────────────────────────
        if self._is_exempt(request.path):
            return self.get_response(request)

        # ── 2. Validar licencia ──────────────────────────────────────────────
        engine = get_engine()
        result = engine.validate()

        # ── 3. Procesar resultado ────────────────────────────────────────────
        if result.status == "NO_LICENSE":
            logger.info(
                "Acceso bloqueado — sin licencia | path=%s ip=%s",
                request.path, self._get_ip(request),
            )
            return redirect("/license/activate/")

        if result.status == "TAMPERED":
            logger.error(
                "Token manipulado detectado | path=%s ip=%s",
                request.path, self._get_ip(request),
            )
            engine.delete_token()
            return redirect("/license/activate/?reason=tampered")

        if result.status == "EXPIRED":
            logger.info(
                "Licencia vencida | expiry=%s path=%s",
                result.expiry_date, request.path,
            )
            return redirect("/license/expired/")

        if result.status == "CLOCK_ROLLBACK":
            logger.error(
                "Rollback de reloj detectado | ip=%s",
                self._get_ip(request),
            )
            engine.delete_token()
            return redirect("/license/activate/?reason=clock")

        # ── 4. Licencia válida — adjuntar al request y continuar ─────────────
        request.license = result

        # Aviso si quedan pocos días (se puede mostrar en templates con {{ request.license_warning }})
        if result.days_remaining <= 7:
            request.license_warning = (
                f"⚠ Tu licencia vence en {result.days_remaining} día(s). "
                f"Contacta a soporte para renovar."
            )
            logger.warning(
                "Licencia por vencer | days_remaining=%s",
                result.days_remaining,
            )

        return self.get_response(request)

    def _is_exempt(self, path: str) -> bool:
        """Retorna True si la ruta no necesita validación de licencia."""
        return path.startswith(self.exempt)

    @staticmethod
    def _get_ip(request) -> str:
        """Extrae la IP real del cliente (considera proxies)."""
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")

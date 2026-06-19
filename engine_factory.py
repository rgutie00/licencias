"""
engine_factory.py — Fase 2
Crea y mantiene una instancia singleton del LicenseEngine
configurada con los valores de settings.py de Django.

Separado del middleware para facilitar el mock en tests.
"""
import logging

from django.conf import settings

from license_engine import LicenseEngine

logger = logging.getLogger("license")

_engine_instance: LicenseEngine | None = None


def get_engine() -> LicenseEngine:
    """
    Retorna el singleton del LicenseEngine.
    Se crea la primera vez que se llama, configurado con Django settings.

    Settings requeridos:
        LICENSE_SECRET_KEY  — clave compartida con el servidor central
        LICENSE_TOKEN_PATH  — ruta del token cifrado en disco
        LICENSE_SERVER_URL  — URL del servidor central (vacío = solo offline)
        LICENSE_API_KEY     — API key para el servidor central

    Settings opcionales:
        LICENSE_MAX_OFFLINE_DAYS — días máximos sin conexión (default: 30)
        LICENSE_HTTP_TIMEOUT     — timeout en segundos para validación online (default: 5.0)
    """
    global _engine_instance

    if _engine_instance is None:
        _engine_instance = LicenseEngine(
            secret_key=getattr(settings, "LICENSE_SECRET_KEY", "CHANGE_IN_PRODUCTION"),
            token_path=getattr(settings, "LICENSE_TOKEN_PATH", "/var/app/license.tok"),
            server_url=getattr(settings, "LICENSE_SERVER_URL", ""),
            api_key=getattr(settings, "LICENSE_API_KEY", ""),
            max_offline_days=getattr(settings, "LICENSE_MAX_OFFLINE_DAYS", 30),
            http_timeout=getattr(settings, "LICENSE_HTTP_TIMEOUT", 5.0),
        )
        logger.debug("LicenseEngine instanciado desde Django settings.")

    return _engine_instance


def reset_engine():
    """
    Reinicia el singleton. Útil en tests para forzar
    reconfiguración con settings diferentes.
    """
    global _engine_instance
    _engine_instance = None

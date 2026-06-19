"""
engine_factory.py — Fábrica singleton del LicenseEngine.

El engine se construye una sola vez por proceso, usando los settings
de Django. Los tests llaman reset_engine() entre cada test para
evitar estado compartido.
"""
from django.conf import settings

from .license_engine import LicenseEngine

_engine_instance: "LicenseEngine | None" = None


def get_engine() -> LicenseEngine:
    """Devuelve el singleton del LicenseEngine, creándolo si hace falta."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = LicenseEngine(
            secret_key=getattr(settings, "LICENSE_SECRET_KEY", "CHANGE_IN_PRODUCTION"),
            token_path=getattr(settings, "LICENSE_TOKEN_PATH", "/var/app/license.tok"),
            server_url=getattr(settings, "LICENSE_SERVER_URL", ""),
            api_key=getattr(settings, "LICENSE_API_KEY", ""),
            max_offline_days=getattr(settings, "LICENSE_MAX_OFFLINE_DAYS", 30),
        )
    return _engine_instance


def reset_engine() -> None:
    """Limpia el singleton. Usado por los tests."""
    global _engine_instance
    _engine_instance = None

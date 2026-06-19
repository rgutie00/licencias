"""
permissions.py — Autenticación de agentes clientes.
Los clientes se autentican con una API Key en el header X-License-Agent-Key.
"""
import logging

from django.conf import settings
from rest_framework.permissions import BasePermission

logger = logging.getLogger("licenses")


class AgentKeyPermission(BasePermission):
    """
    Verifica que el request tenga el header X-License-Agent-Key correcto.
    Se aplica a todos los endpoints de la API de licencias.
    """

    message = "API Key inválida o ausente."

    def has_permission(self, request, view):
        api_key = request.headers.get("X-License-Agent-Key", "")
        expected = getattr(settings, "LICENSE_AGENT_API_KEY", "")

        if not api_key:
            logger.warning(
                "Request sin API Key | ip=%s path=%s",
                self._get_ip(request), request.path,
            )
            return False

        if not expected:
            logger.error("LICENSE_AGENT_API_KEY no configurada en settings.")
            return False

        valid = hmac_compare(api_key, expected)
        if not valid:
            logger.warning(
                "API Key inválida | ip=%s",
                self._get_ip(request),
            )
        return valid

    @staticmethod
    def _get_ip(request) -> str:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")


def hmac_compare(a: str, b: str) -> bool:
    """Comparación segura resistente a timing attacks."""
    import hmac as _hmac
    return _hmac.compare_digest(
        a.encode() if isinstance(a, str) else a,
        b.encode() if isinstance(b, str) else b,
    )

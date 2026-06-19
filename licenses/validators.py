"""
validators.py — Validación HMAC server-side.
El servidor regenera la clave esperada y la compara con la recibida.
Mismo algoritmo que license_engine.py del cliente.
"""
import base64
import hashlib
import hmac

from django.conf import settings

VERSION_SALT = b"v1.0"


def normalize_mac(raw: str) -> str:
    """Normaliza MAC: sin separadores, uppercase."""
    return raw.replace(":", "").replace("-", "").replace(".", "").upper().strip()


def normalize_nit(raw: str) -> str:
    """Normaliza NIT: sin espacios, uppercase."""
    return raw.strip().upper()


def generate_license_key(mac: str, nit: str) -> str:
    """
    Genera la clave de licencia esperada para un par MAC+NIT.
    Determinístico: misma entrada → misma clave siempre.
    Debe producir el mismo resultado que LicenseEngine.generate_key() del cliente.
    """
    secret = getattr(settings, "LICENSE_SECRET_KEY", "CHANGE_IN_PRODUCTION")
    if isinstance(secret, str):
        secret = secret.encode()

    mac_norm = normalize_mac(mac)
    nit_norm = normalize_nit(nit)

    message = f"{mac_norm}:{nit_norm}".encode() + VERSION_SALT
    digest = hmac.new(secret, message, hashlib.sha256).digest()

    b32 = base64.b32encode(digest).decode()
    return "-".join(b32[i:i + 4] for i in range(0, 16, 4))


def verify_license_key(mac: str, nit: str, key: str) -> bool:
    """
    Verifica que la clave recibida corresponde al par MAC+NIT dados.
    Usa hmac.compare_digest para resistir timing attacks.
    """
    expected = generate_license_key(mac, nit)
    return hmac.compare_digest(expected, key)

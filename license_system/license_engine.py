"""
license_engine.py — Fase 1
Motor criptográfico del sistema de licencias.

Diseño:
  - Independiente de Django: recibe config como parámetros, no de settings.
  - Identificación: MAC del servidor + NIT de la empresa.
  - Token local cifrado con Fernet (clave derivada de la MAC → hardware-bound).
  - Validación: online → servidor central | offline → fecha local vs expiry.
  - Detección de rollback de reloj y manipulación de token.

Uso desde Django (middleware):
    engine = LicenseEngine(
        secret_key=settings.LICENSE_SECRET_KEY,
        token_path=settings.LICENSE_TOKEN_PATH,
        server_url=settings.LICENSE_SERVER_URL,
        api_key=settings.LICENSE_API_KEY,
    )
    result = engine.validate()
"""

import base64
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
import psutil
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger("license")

# Salt de versión — cambiar invalida todas las licencias de versiones anteriores
VERSION_SALT = b"v1.0"

# Máximo de días offline permitidos antes de forzar reconexión
DEFAULT_MAX_OFFLINE_DAYS = 30


# ─────────────────────────────────────────────
#  RESULTADO DE VALIDACIÓN
# ─────────────────────────────────────────────

@dataclass
class LicenseResult:
    """
    Resultado de una validación de licencia.

    status posibles:
        VALID          — licencia activa y vigente
        NO_LICENSE     — no existe token local
        EXPIRED        — licencia vencida (online u offline)
        TAMPERED       — token manipulado o ilegible
        CLOCK_ROLLBACK — fecha del sistema retrocedió (posible trampa)
    """
    status: str
    expiry_date: Optional[datetime] = None
    days_remaining: int = 0
    license_type: str = "commercial"
    message: str = ""
    offline_mode: bool = False

    @property
    def is_valid(self) -> bool:
        return self.status == "VALID"

    def __str__(self) -> str:
        return f"LicenseResult(status={self.status}, days_remaining={self.days_remaining})"


# ─────────────────────────────────────────────
#  MOTOR PRINCIPAL
# ─────────────────────────────────────────────

class LicenseEngine:
    """
    Motor criptográfico del sistema de licencias.

    Args:
        secret_key:        Clave secreta compartida con el servidor central.
                           En producción viene de variable de entorno.
        token_path:        Ruta al archivo del token cifrado en disco.
        server_url:        URL base del servidor central de licencias.
        api_key:           API Key para autenticar requests al servidor.
        max_offline_days:  Máximo de días sin conexión permitidos.
        http_timeout:      Timeout en segundos para llamadas al servidor.
    """

    def __init__(
        self,
        secret_key: str = "CHANGE_IN_PRODUCTION",
        token_path: str = "/var/app/license.tok",
        server_url: str = "",
        api_key: str = "",
        max_offline_days: int = DEFAULT_MAX_OFFLINE_DAYS,
        http_timeout: float = 5.0,
    ):
        self._secret = secret_key.encode() if isinstance(secret_key, str) else secret_key
        self._token_path = Path(token_path)
        self._server_url = server_url.rstrip("/")
        self._api_key = api_key
        self._max_offline_days = max_offline_days
        self._http_timeout = http_timeout

    # ── MAC ─────────────────────────────────────────────────────────────────

    def get_server_mac(self) -> str:
        """
        Lee la MAC de la primera interfaz de red activa del servidor.
        Ignora loopback (lo/lo0) y MACs nulas.

        Returns:
            MAC normalizada: sin separadores, uppercase. Ej: "AABBCCDDEEFF"

        Raises:
            RuntimeError: si no se encuentra ninguna interfaz válida.
        """
        for iface_name, addrs in psutil.net_if_addrs().items():
            if iface_name.lower() in ("lo", "lo0", "loopback"):
                continue
            for addr in addrs:
                if addr.family == psutil.AF_LINK and addr.address:
                    mac = self._normalize_mac(addr.address)
                    if mac and mac != "000000000000":
                        logger.debug("MAC del servidor detectada: %s...", mac[:6])
                        return mac

        raise RuntimeError(
            "No se encontró una interfaz de red válida en el servidor. "
            "Verifica que el servidor tenga al menos una NIC activa."
        )

    @staticmethod
    def _normalize_mac(raw: str) -> str:
        """
        Normaliza una MAC a formato sin separadores, uppercase.

        Acepta: "AA:BB:CC:DD:EE:FF", "AA-BB-CC-DD-EE-FF", "AABBCCDDEEFF"
        Retorna: "AABBCCDDEEFF"
        """
        return raw.replace(":", "").replace("-", "").replace(".", "").upper().strip()

    # ── GENERACIÓN DE CLAVE ─────────────────────────────────────────────────

    def generate_key(self, mac: str, nit: str) -> str:
        """
        Genera la clave de licencia: HMAC-SHA256(mac + nit) con VERSION_SALT.

        Determinístico: misma MAC + NIT → misma clave siempre.
        Formato de salida: "XXXX-XXXX-XXXX-XXXX" (legible para humanos).

        Args:
            mac: MAC normalizada del servidor (resultado de get_server_mac()).
            nit: NIT de la empresa cliente (se normaliza internamente).

        Returns:
            Clave en formato "A3KL-7PQR-XZ2W-M9BN"
        """
        mac_norm = self._normalize_mac(mac)
        nit_norm = nit.strip().upper()

        message = f"{mac_norm}:{nit_norm}".encode() + VERSION_SALT
        digest = hmac.new(self._secret, message, hashlib.sha256).digest()

        b32 = base64.b32encode(digest).decode()
        return "-".join(b32[i:i + 4] for i in range(0, 16, 4))

    def verify_key(self, mac: str, nit: str, key: str) -> bool:
        """
        Verifica que una clave corresponde al par MAC+NIT dados.
        Usa compare_digest para resistir timing attacks.
        """
        expected = self.generate_key(mac, nit)
        return hmac.compare_digest(expected, key)

    # ── CIFRADO DEL TOKEN ───────────────────────────────────────────────────

    def _derive_fernet_key(self, mac: str) -> bytes:
        """
        Deriva la clave Fernet a partir de la MAC del servidor.

        Hardware-bound: si el token se copia a otro servidor con distinta MAC,
        la clave derivada es diferente y el descifrado falla con InvalidToken.

        Usa PBKDF2-HMAC-SHA256 con 480.000 iteraciones (resistente a brute-force).
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._normalize_mac(mac).encode(),
            iterations=480_000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self._secret))

    def save_token(self, mac: str, payload: dict) -> None:
        """
        Cifra el payload con Fernet y lo guarda en disco.

        El payload incluye: license_key, nit, expiry, license_type,
        last_online_check. Solo legible en el mismo servidor (misma MAC).

        Args:
            mac:     MAC del servidor actual.
            payload: Diccionario con los datos de la licencia.
        """
        fernet = Fernet(self._derive_fernet_key(mac))
        encrypted = fernet.encrypt(json.dumps(payload, default=str).encode())

        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        self._token_path.write_bytes(encrypted)
        logger.info("Token de licencia guardado en %s", self._token_path)

    def load_token(self, mac: str) -> "dict | None | str":
        """
        Descifra y carga el token local.

        Returns:
            dict   → token válido descifrado
            None   → no existe el archivo
            'TAMPERED' → archivo existe pero no se puede descifrar
                         (MAC diferente, archivo corrupto o modificado)
        """
        if not self._token_path.exists():
            logger.debug("Token no encontrado en %s", self._token_path)
            return None

        try:
            fernet = Fernet(self._derive_fernet_key(mac))
            raw = fernet.decrypt(self._token_path.read_bytes())
            return json.loads(raw)
        except (InvalidToken, json.JSONDecodeError, Exception) as e:
            logger.error("Error al descifrar token: %s", e)
            return "TAMPERED"

    def delete_token(self) -> None:
        """Elimina el token local del disco."""
        if self._token_path.exists():
            self._token_path.unlink()
            logger.info("Token eliminado de %s", self._token_path)

    # ── VALIDACIÓN ONLINE ───────────────────────────────────────────────────

    def validate_online(self, mac: str, key: str, nit: str) -> "LicenseResult | None":
        """
        Valida la licencia contra el servidor central.

        Returns:
            LicenseResult si el servidor respondió (válida o no).
            None si no hay conexión (timeout, DNS, etc.) → usar offline.
        """
        if not self._server_url:
            logger.debug("SERVER_URL no configurado, skipping validación online.")
            return None

        endpoint = f"{self._server_url}/licenses/validate"
        payload = {
            "mac": mac,
            "nit": nit,
            "license_key": key,
            "system_date": datetime.now(timezone.utc).isoformat(),
        }
        headers = {"X-License-Agent-Key": self._api_key}

        try:
            response = httpx.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self._http_timeout,
            )

            if response.status_code == 200:
                data = response.json()
                expiry = datetime.fromisoformat(data["expiry_date"])
                delta = max((expiry - datetime.now(timezone.utc)).days, 0)
                return LicenseResult(
                    status="VALID",
                    expiry_date=expiry,
                    days_remaining=delta,
                    license_type=data.get("license_type", "commercial"),
                )

            if response.status_code == 402:
                return LicenseResult(
                    status="EXPIRED",
                    message="Licencia vencida según el servidor.",
                )

            if response.status_code == 403:
                return LicenseResult(
                    status="EXPIRED",
                    message="Licencia revocada por el administrador.",
                )

            logger.warning("Servidor respondió %s", response.status_code)
            return LicenseResult(
                status="EXPIRED",
                message=f"Servidor rechazó la licencia (HTTP {response.status_code}).",
            )

        except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
            logger.info("Sin conexión al servidor de licencias: %s", e)
            return None  # Fallback a offline

    # ── VALIDACIÓN OFFLINE ──────────────────────────────────────────────────

    def validate_offline(self, token: dict) -> LicenseResult:
        """
        Valida la licencia usando solo el token local (sin red).

        Comprueba:
          1. Que la fecha del sistema no haya retrocedido (rollback).
          2. Que la fecha del sistema no supere expiry_date.
          3. Que no se hayan superado los días offline permitidos.

        Args:
            token: Diccionario descifrado del token local.

        Returns:
            LicenseResult con status VALID, EXPIRED o CLOCK_ROLLBACK.
        """
        now = datetime.now(timezone.utc)

        # Parsear fechas del token
        try:
            expiry = datetime.fromisoformat(token["expiry"])
        except (KeyError, ValueError):
            return LicenseResult(status="EXPIRED", message="Token con fecha de vencimiento inválida.")

        try:
            last_check = datetime.fromisoformat(token.get("last_online_check", "2000-01-01T00:00:00+00:00"))
        except ValueError:
            last_check = datetime(2000, 1, 1, tzinfo=timezone.utc)

        # ── Detectar rollback de reloj ──────────────────────────────────────
        # Si la fecha actual es anterior al último check online conocido,
        # alguien retrocedió el reloj del sistema para extender la licencia.
        if now < last_check:
            logger.error(
                "CLOCK ROLLBACK detectado: ahora=%s, last_check=%s",
                now.isoformat(), last_check.isoformat(),
            )
            return LicenseResult(
                status="CLOCK_ROLLBACK",
                message=(
                    f"La fecha del sistema ({now.strftime('%d/%m/%Y %H:%M')}) "
                    f"es anterior a la última verificación conocida "
                    f"({last_check.strftime('%d/%m/%Y %H:%M')}). "
                    "Posible manipulación del reloj."
                ),
            )

        # ── Verificar que no se superaron los días offline máximos ──────────
        offline_days = (now - last_check).days
        if offline_days > self._max_offline_days:
            return LicenseResult(
                status="EXPIRED",
                message=(
                    f"Límite de uso offline superado ({offline_days} días sin conexión, "
                    f"máximo {self._max_offline_days}). Conecte el servidor para renovar."
                ),
            )

        # ── Verificar vencimiento ────────────────────────────────────────────
        if now > expiry:
            return LicenseResult(
                status="EXPIRED",
                expiry_date=expiry,
                message=f"Licencia vencida el {expiry.strftime('%d/%m/%Y')}.",
                offline_mode=True,
            )

        delta = max((expiry - now).days, 0)
        return LicenseResult(
            status="VALID",
            expiry_date=expiry,
            days_remaining=delta,
            license_type=token.get("license_type", "commercial"),
            offline_mode=True,
        )

    # ── PUNTO DE ENTRADA PRINCIPAL ──────────────────────────────────────────

    def validate(self) -> LicenseResult:
        """
        Valida la licencia. Llamado por LicenseMiddleware en cada request.

        Orden de validación:
          1. Leer MAC del servidor
          2. Cargar y descifrar token local
          3. Intentar validación online → si hay red, actualizar token
          4. Si no hay red → validación offline con fecha local

        Returns:
            LicenseResult con el resultado final de la validación.
        """
        # 1. Obtener MAC del servidor
        try:
            mac = self.get_server_mac()
        except RuntimeError as e:
            logger.error("No se pudo obtener MAC del servidor: %s", e)
            return LicenseResult(status="NO_LICENSE", message=str(e))

        # 2. Cargar token local
        token = self.load_token(mac)

        if token is None:
            return LicenseResult(status="NO_LICENSE", message="No se encontró licencia instalada.")

        if token == "TAMPERED":
            return LicenseResult(
                status="TAMPERED",
                message="El archivo de licencia fue modificado o está corrupto.",
            )

        key = token.get("license_key", "")
        nit = token.get("nit", "")

        # 3. Intentar validación online
        online_result = self.validate_online(mac, key, nit)

        if online_result is not None:
            # Servidor respondió — si es válida, actualizar el token local
            if online_result.is_valid and online_result.expiry_date:
                token["expiry"] = online_result.expiry_date.isoformat()
                token["last_online_check"] = datetime.now(timezone.utc).isoformat()
                self.save_token(mac, token)
                logger.info("Token actualizado tras validación online exitosa.")
            return online_result

        # 4. Sin conexión → validación offline
        logger.info("Validando en modo offline.")
        return self.validate_offline(token)

    # ── UTILIDADES ──────────────────────────────────────────────────────────

    def build_activation_payload(self, nit: str, client_name: str) -> dict:
        """
        Construye el payload de activación para enviar al servidor.
        Lee la MAC del servidor automáticamente.

        Returns:
            Dict listo para hacer POST a /licenses/activate
        """
        mac = self.get_server_mac()
        key = self.generate_key(mac, nit)
        return {
            "mac": mac,
            "nit": nit.strip().upper(),
            "client_name": client_name.strip(),
            "license_key": key,
            "system_date": datetime.now(timezone.utc).isoformat(),
        }

    def activate_from_response(self, mac: str, nit: str, response_data: dict) -> None:
        """
        Procesa la respuesta del servidor y guarda el token cifrado.

        Args:
            mac:           MAC del servidor actual.
            nit:           NIT de la empresa.
            response_data: Respuesta JSON del servidor de licencias.
        """
        token = {
            "license_key": self.generate_key(mac, nit),
            "nit": nit.strip().upper(),
            "client_name": response_data.get("client_name", ""),
            "expiry": response_data["expiry_date"],
            "license_type": response_data.get("license_type", "commercial"),
            "last_online_check": response_data.get(
                "server_time",
                datetime.now(timezone.utc).isoformat()
            ),
        }
        self.save_token(mac, token)
        logger.info("Licencia activada y token guardado para NIT=%s", nit)

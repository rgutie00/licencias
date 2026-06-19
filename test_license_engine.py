"""
test_license_engine.py — Fase 1
Tests unitarios del LicenseEngine.

Cómo ejecutar:
    pip install pytest psutil httpx cryptography
    pytest test_license_engine.py -v

No requiere red, ni Django, ni archivos reales en disco.
Usa tmp_path de pytest para archivos temporales.
"""

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from license_engine import LicenseEngine, LicenseResult

# ─────────────────────────────────────────────────────────────
#  FIXTURES
# ─────────────────────────────────────────────────────────────

SECRET = "TEST_SECRET_KEY_FASE1"
FAKE_MAC = "AABBCCDDEEFF"
FAKE_MAC_COLONS = "AA:BB:CC:DD:EE:FF"
FAKE_MAC_DASHES = "AA-BB-CC-DD-EE-FF"
FAKE_NIT = "900123456-7"
FAKE_NAME = "Empresa Test S.A.S"


@pytest.fixture
def engine(tmp_path):
    """Engine con token en directorio temporal."""
    token_path = tmp_path / "license.tok"
    return LicenseEngine(
        secret_key=SECRET,
        token_path=str(token_path),
        server_url="",  # Sin servidor en fase 1
        api_key="",
        max_offline_days=30,
    )


@pytest.fixture
def future_expiry():
    return (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()


@pytest.fixture
def past_expiry():
    return (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()


@pytest.fixture
def recent_check():
    return (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()


@pytest.fixture
def future_check():
    """Check en el futuro → simula rollback de reloj."""
    return (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()


def make_token(engine, mac, nit, expiry, last_check=None, license_type="commercial"):
    """Helper: crea y guarda un token válido."""
    if last_check is None:
        last_check = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    payload = {
        "license_key": engine.generate_key(mac, nit),
        "nit": nit,
        "client_name": FAKE_NAME,
        "expiry": expiry,
        "license_type": license_type,
        "last_online_check": last_check,
    }
    engine.save_token(mac, payload)
    return payload


# ─────────────────────────────────────────────────────────────
#  1. NORMALIZACIÓN DE MAC
# ─────────────────────────────────────────────────────────────

class TestNormalizeMac:

    def test_mac_con_dos_puntos(self, engine):
        assert engine._normalize_mac("AA:BB:CC:DD:EE:FF") == "AABBCCDDEEFF"

    def test_mac_con_guiones(self, engine):
        assert engine._normalize_mac("AA-BB-CC-DD-EE-FF") == "AABBCCDDEEFF"

    def test_mac_ya_normalizada(self, engine):
        assert engine._normalize_mac("AABBCCDDEEFF") == "AABBCCDDEEFF"

    def test_mac_minusculas(self, engine):
        assert engine._normalize_mac("aa:bb:cc:dd:ee:ff") == "AABBCCDDEEFF"

    def test_mac_mixta(self, engine):
        assert engine._normalize_mac("Aa:Bb:Cc:Dd:Ee:Ff") == "AABBCCDDEEFF"

    def test_mac_con_puntos(self, engine):
        assert engine._normalize_mac("AABB.CCDD.EEFF") == "AABBCCDDEEFF"

    def test_mac_con_espacios(self, engine):
        assert engine._normalize_mac("  AA:BB:CC:DD:EE:FF  ") == "AABBCCDDEEFF"


# ─────────────────────────────────────────────────────────────
#  2. GENERACIÓN DE CLAVE
# ─────────────────────────────────────────────────────────────

class TestGenerateKey:

    def test_genera_formato_correcto(self, engine):
        key = engine.generate_key(FAKE_MAC, FAKE_NIT)
        partes = key.split("-")
        assert len(partes) == 4
        assert all(len(p) == 4 for p in partes)

    def test_determinismo_misma_entrada(self, engine):
        key1 = engine.generate_key(FAKE_MAC, FAKE_NIT)
        key2 = engine.generate_key(FAKE_MAC, FAKE_NIT)
        assert key1 == key2

    def test_mac_formatos_equivalentes(self, engine):
        """Distintos formatos de MAC deben producir la misma clave."""
        key1 = engine.generate_key(FAKE_MAC, FAKE_NIT)
        key2 = engine.generate_key(FAKE_MAC_COLONS, FAKE_NIT)
        key3 = engine.generate_key(FAKE_MAC_DASHES, FAKE_NIT)
        assert key1 == key2 == key3

    def test_nit_normalizado(self, engine):
        """NIT con espacios y minúsculas debe dar la misma clave."""
        key1 = engine.generate_key(FAKE_MAC, "900123456-7")
        key2 = engine.generate_key(FAKE_MAC, "  900123456-7  ")
        key3 = engine.generate_key(FAKE_MAC, "900123456-7".lower())
        assert key1 == key2 == key3

    def test_mac_diferente_da_clave_diferente(self, engine):
        key1 = engine.generate_key("AABBCCDDEEFF", FAKE_NIT)
        key2 = engine.generate_key("FFEEDDCCBBAA", FAKE_NIT)
        assert key1 != key2

    def test_nit_diferente_da_clave_diferente(self, engine):
        key1 = engine.generate_key(FAKE_MAC, "900000001-0")
        key2 = engine.generate_key(FAKE_MAC, "900000002-0")
        assert key1 != key2

    def test_secret_diferente_da_clave_diferente(self, tmp_path):
        e1 = LicenseEngine(secret_key="SECRET_A", token_path=str(tmp_path / "t1.tok"))
        e2 = LicenseEngine(secret_key="SECRET_B", token_path=str(tmp_path / "t2.tok"))
        assert e1.generate_key(FAKE_MAC, FAKE_NIT) != e2.generate_key(FAKE_MAC, FAKE_NIT)


# ─────────────────────────────────────────────────────────────
#  3. VERIFICACIÓN DE CLAVE
# ─────────────────────────────────────────────────────────────

class TestVerifyKey:

    def test_clave_correcta(self, engine):
        key = engine.generate_key(FAKE_MAC, FAKE_NIT)
        assert engine.verify_key(FAKE_MAC, FAKE_NIT, key) is True

    def test_clave_incorrecta(self, engine):
        assert engine.verify_key(FAKE_MAC, FAKE_NIT, "XXXX-XXXX-XXXX-XXXX") is False

    def test_mac_incorrecta(self, engine):
        key = engine.generate_key(FAKE_MAC, FAKE_NIT)
        assert engine.verify_key("FFEEDDCCBBAA", FAKE_NIT, key) is False

    def test_nit_incorrecto(self, engine):
        key = engine.generate_key(FAKE_MAC, FAKE_NIT)
        assert engine.verify_key(FAKE_MAC, "111111111-1", key) is False

    def test_clave_vacia(self, engine):
        assert engine.verify_key(FAKE_MAC, FAKE_NIT, "") is False


# ─────────────────────────────────────────────────────────────
#  4. CIFRADO Y DESCIFRADO DEL TOKEN
# ─────────────────────────────────────────────────────────────

class TestTokenStorage:

    def test_guardar_y_cargar(self, engine, future_expiry, recent_check):
        payload = {
            "license_key": engine.generate_key(FAKE_MAC, FAKE_NIT),
            "nit": FAKE_NIT,
            "expiry": future_expiry,
            "last_online_check": recent_check,
        }
        engine.save_token(FAKE_MAC, payload)
        loaded = engine.load_token(FAKE_MAC)

        assert loaded is not None
        assert loaded != "TAMPERED"
        assert loaded["nit"] == FAKE_NIT
        assert loaded["expiry"] == future_expiry

    def test_token_no_existe(self, engine):
        result = engine.load_token(FAKE_MAC)
        assert result is None

    def test_token_mac_diferente_tampered(self, engine, future_expiry, recent_check):
        """Token cifrado con MAC_A no se puede descifrar con MAC_B."""
        payload = {"expiry": future_expiry, "last_online_check": recent_check}
        engine.save_token("AABBCCDDEEFF", payload)

        result = engine.load_token("FFEEDDCCBBAA")  # MAC diferente
        assert result == "TAMPERED"

    def test_token_archivo_corrupto(self, engine):
        """Archivo con bytes aleatorios debe retornar TAMPERED."""
        engine._token_path.parent.mkdir(parents=True, exist_ok=True)
        engine._token_path.write_bytes(b"\x00\xff\xab\xcd" * 100)
        assert engine.load_token(FAKE_MAC) == "TAMPERED"

    def test_token_archivo_vacio(self, engine):
        engine._token_path.parent.mkdir(parents=True, exist_ok=True)
        engine._token_path.write_bytes(b"")
        assert engine.load_token(FAKE_MAC) == "TAMPERED"

    def test_token_texto_plano(self, engine):
        """Archivo con JSON sin cifrar debe retornar TAMPERED."""
        engine._token_path.parent.mkdir(parents=True, exist_ok=True)
        engine._token_path.write_text('{"expiry": "2030-01-01"}', encoding="utf-8")
        assert engine.load_token(FAKE_MAC) == "TAMPERED"

    def test_delete_token(self, engine, future_expiry, recent_check):
        make_token(engine, FAKE_MAC, FAKE_NIT, future_expiry, recent_check)
        assert engine._token_path.exists()

        engine.delete_token()
        assert not engine._token_path.exists()

    def test_delete_token_no_existe(self, engine):
        """Eliminar token inexistente no debe lanzar error."""
        engine.delete_token()  # No debe fallar

    def test_payload_completo_roundtrip(self, engine):
        """Todos los campos del payload deben sobrevivir el cifrado/descifrado."""
        expiry = (datetime.now(timezone.utc) + timedelta(days=180)).isoformat()
        check = datetime.now(timezone.utc).isoformat()
        payload = {
            "license_key": "A3KL-7PQR-XZ2W-M9BN",
            "nit": FAKE_NIT,
            "client_name": FAKE_NAME,
            "expiry": expiry,
            "license_type": "trial",
            "last_online_check": check,
        }
        engine.save_token(FAKE_MAC, payload)
        loaded = engine.load_token(FAKE_MAC)

        for key, value in payload.items():
            assert loaded[key] == value, f"Campo '{key}' no coincide"


# ─────────────────────────────────────────────────────────────
#  5. VALIDACIÓN OFFLINE
# ─────────────────────────────────────────────────────────────

class TestValidateOffline:

    def test_licencia_vigente(self, engine, future_expiry, recent_check):
        token = {
            "expiry": future_expiry,
            "last_online_check": recent_check,
            "license_type": "commercial",
        }
        result = engine.validate_offline(token)
        assert result.status == "VALID"
        assert result.days_remaining > 0
        assert result.offline_mode is True

    def test_licencia_vencida(self, engine, past_expiry, recent_check):
        token = {
            "expiry": past_expiry,
            "last_online_check": recent_check,
        }
        result = engine.validate_offline(token)
        assert result.status == "EXPIRED"

    def test_rollback_de_reloj(self, engine, future_expiry, future_check):
        """Si last_check está en el futuro, el reloj fue retrocedido."""
        token = {
            "expiry": future_expiry,
            "last_online_check": future_check,
        }
        result = engine.validate_offline(token)
        assert result.status == "CLOCK_ROLLBACK"
        assert "reloj" in result.message.lower()

    def test_limite_offline_superado(self, engine):
        """Más días offline que el máximo permitido → EXPIRED."""
        engine_strict = LicenseEngine(
            secret_key=SECRET,
            token_path=str(engine._token_path),
            max_offline_days=5,
        )
        last_check = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        expiry = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        token = {"expiry": expiry, "last_online_check": last_check}

        result = engine_strict.validate_offline(token)
        assert result.status == "EXPIRED"
        assert "offline" in result.message.lower()

    def test_limite_offline_justo(self, engine):
        """Exactamente en el límite de días offline → VALID."""
        last_check = (datetime.now(timezone.utc) - timedelta(days=29)).isoformat()
        expiry = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        token = {
            "expiry": expiry,
            "last_online_check": last_check,
            "license_type": "commercial",
        }
        result = engine.validate_offline(token)
        assert result.status == "VALID"

    def test_vence_hoy_boundary(self, engine, recent_check):
        """Licencia que vence exactamente hoy (futuro cercano) → VALID."""
        expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        token = {
            "expiry": expiry,
            "last_online_check": recent_check,
            "license_type": "commercial",
        }
        result = engine.validate_offline(token)
        assert result.status == "VALID"
        assert result.days_remaining == 0

    def test_token_sin_expiry(self, engine, recent_check):
        """Token sin campo expiry debe retornar EXPIRED."""
        token = {"last_online_check": recent_check}
        result = engine.validate_offline(token)
        assert result.status == "EXPIRED"

    def test_license_type_trial(self, engine, recent_check):
        expiry = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        token = {
            "expiry": expiry,
            "last_online_check": recent_check,
            "license_type": "trial",
        }
        result = engine.validate_offline(token)
        assert result.status == "VALID"
        assert result.license_type == "trial"


# ─────────────────────────────────────────────────────────────
#  6. VALIDACIÓN COMPLETA (validate())
# ─────────────────────────────────────────────────────────────

class TestValidate:

    def test_sin_token_retorna_no_license(self, engine):
        with patch.object(engine, "get_server_mac", return_value=FAKE_MAC):
            result = engine.validate()
        assert result.status == "NO_LICENSE"

    def test_token_vigente_offline(self, engine, future_expiry, recent_check):
        make_token(engine, FAKE_MAC, FAKE_NIT, future_expiry, recent_check)
        with patch.object(engine, "get_server_mac", return_value=FAKE_MAC):
            # Sin servidor configurado → modo offline
            result = engine.validate()
        assert result.status == "VALID"
        assert result.offline_mode is True

    def test_token_vencido_offline(self, engine, past_expiry, recent_check):
        make_token(engine, FAKE_MAC, FAKE_NIT, past_expiry, recent_check)
        with patch.object(engine, "get_server_mac", return_value=FAKE_MAC):
            result = engine.validate()
        assert result.status == "EXPIRED"

    def test_token_manipulado(self, engine):
        engine._token_path.parent.mkdir(parents=True, exist_ok=True)
        engine._token_path.write_bytes(b"datos_corruptos_xyzxyz")
        with patch.object(engine, "get_server_mac", return_value=FAKE_MAC):
            result = engine.validate()
        assert result.status == "TAMPERED"

    def test_rollback_reloj(self, engine, future_expiry, future_check):
        make_token(engine, FAKE_MAC, FAKE_NIT, future_expiry, future_check)
        with patch.object(engine, "get_server_mac", return_value=FAKE_MAC):
            result = engine.validate()
        assert result.status == "CLOCK_ROLLBACK"

    def test_error_obtener_mac(self, engine):
        with patch.object(engine, "get_server_mac", side_effect=RuntimeError("No NIC")):
            result = engine.validate()
        assert result.status == "NO_LICENSE"
        assert "No NIC" in result.message

    def test_online_actualiza_token(self, engine, future_expiry, recent_check):
        """Si el servidor responde OK, el token local debe actualizarse."""
        make_token(engine, FAKE_MAC, FAKE_NIT, recent_check, recent_check)

        nueva_expiry = (datetime.now(timezone.utc) + timedelta(days=365))
        mock_result = LicenseResult(
            status="VALID",
            expiry_date=nueva_expiry,
            days_remaining=365,
            license_type="commercial",
        )

        with patch.object(engine, "get_server_mac", return_value=FAKE_MAC):
            with patch.object(engine, "validate_online", return_value=mock_result):
                result = engine.validate()

        assert result.status == "VALID"

        # Verificar que el token fue actualizado con la nueva expiry
        updated = engine.load_token(FAKE_MAC)
        assert updated is not None
        assert updated != "TAMPERED"
        stored_expiry = datetime.fromisoformat(updated["expiry"])
        assert abs((stored_expiry - nueva_expiry).total_seconds()) < 2

    def test_online_falla_fallback_offline(self, engine, future_expiry, recent_check):
        """Si el servidor no responde, debe usar validación offline."""
        make_token(engine, FAKE_MAC, FAKE_NIT, future_expiry, recent_check)

        with patch.object(engine, "get_server_mac", return_value=FAKE_MAC):
            with patch.object(engine, "validate_online", return_value=None):
                result = engine.validate()

        assert result.status == "VALID"
        assert result.offline_mode is True


# ─────────────────────────────────────────────────────────────
#  7. BUILD ACTIVATION PAYLOAD
# ─────────────────────────────────────────────────────────────

class TestActivationPayload:

    def test_campos_requeridos(self, engine):
        with patch.object(engine, "get_server_mac", return_value=FAKE_MAC):
            payload = engine.build_activation_payload(FAKE_NIT, FAKE_NAME)

        assert "mac" in payload
        assert "nit" in payload
        assert "client_name" in payload
        assert "license_key" in payload
        assert "system_date" in payload

    def test_nit_normalizado_en_payload(self, engine):
        with patch.object(engine, "get_server_mac", return_value=FAKE_MAC):
            payload = engine.build_activation_payload("  900123456-7  ", FAKE_NAME)
        assert payload["nit"] == "900123456-7"

    def test_clave_valida_en_payload(self, engine):
        with patch.object(engine, "get_server_mac", return_value=FAKE_MAC):
            payload = engine.build_activation_payload(FAKE_NIT, FAKE_NAME)
        key = payload["license_key"]
        parts = key.split("-")
        assert len(parts) == 4
        assert all(len(p) == 4 for p in parts)


# ─────────────────────────────────────────────────────────────
#  8. ACTIVATE FROM RESPONSE
# ─────────────────────────────────────────────────────────────

class TestActivateFromResponse:

    def test_guarda_token_correctamente(self, engine):
        expiry = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        response_data = {
            "expiry_date": expiry,
            "license_type": "commercial",
            "server_time": datetime.now(timezone.utc).isoformat(),
        }
        engine.activate_from_response(FAKE_MAC, FAKE_NIT, response_data)

        token = engine.load_token(FAKE_MAC)
        assert token is not None
        assert token != "TAMPERED"
        assert token["nit"] == FAKE_NIT
        assert token["expiry"] == expiry
        assert token["license_type"] == "commercial"

    def test_token_trial(self, engine):
        expiry = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        response_data = {
            "expiry_date": expiry,
            "license_type": "trial",
        }
        engine.activate_from_response(FAKE_MAC, FAKE_NIT, response_data)
        token = engine.load_token(FAKE_MAC)
        assert token["license_type"] == "trial"


# ─────────────────────────────────────────────────────────────
#  9. RESULTADO - LicenseResult
# ─────────────────────────────────────────────────────────────

class TestLicenseResult:

    def test_is_valid_true(self):
        r = LicenseResult(status="VALID")
        assert r.is_valid is True

    def test_is_valid_false(self):
        for status in ("NO_LICENSE", "EXPIRED", "TAMPERED", "CLOCK_ROLLBACK"):
            r = LicenseResult(status=status)
            assert r.is_valid is False, f"Falló para status={status}"

    def test_str(self):
        r = LicenseResult(status="VALID", days_remaining=30)
        assert "VALID" in str(r)
        assert "30" in str(r)

"""
test_api.py — Fase 3
Tests de integración de la API del servidor central de licencias.

Cómo ejecutar:
    pytest test_api.py -v --tb=short

Usa SQLite en memoria — no requiere PostgreSQL real.
"""
import base64
import hashlib
import hmac
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from licenses.models import AuditLog, Client, License
from licenses.validators import generate_license_key

# ─────────────────────────────────────────────────────────────
#  CONSTANTES DE TEST
# ─────────────────────────────────────────────────────────────

AGENT_API_KEY = "test-agent-key-fase3"
FAKE_MAC      = "AABBCCDDEEFF"
FAKE_NIT      = "900123456-7"
FAKE_NAME     = "Empresa Test S.A.S"
HEADERS       = {"HTTP_X_LICENSE_AGENT_KEY": AGENT_API_KEY}


# ─────────────────────────────────────────────────────────────
#  FIXTURES
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def valid_key(settings):
    """Genera clave HMAC válida para FAKE_MAC + FAKE_NIT."""
    settings.LICENSE_SECRET_KEY = "TEST_SECRET_FASE3"
    settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
    return generate_license_key(FAKE_MAC, FAKE_NIT)


@pytest.fixture
def existing_client():
    return Client.objects.create(
        mac=FAKE_MAC, nit=FAKE_NIT, name=FAKE_NAME,
    )


@pytest.fixture
def active_license(existing_client):
    return License.objects.create(
        client=existing_client,
        license_type="commercial",
        status="active",
        expiry_date=timezone.now() + timedelta(days=365),
    )


@pytest.fixture
def expired_license(existing_client):
    return License.objects.create(
        client=existing_client,
        license_type="commercial",
        status="expired",
        expiry_date=timezone.now() - timedelta(days=1),
    )


def activation_payload(key):
    return {
        "mac": FAKE_MAC,
        "nit": FAKE_NIT,
        "client_name": FAKE_NAME,
        "license_key": key,
    }


# ─────────────────────────────────────────────────────────────
#  1. ENDPOINT /activate
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestActivateEndpoint:

    def test_activacion_exitosa(self, api_client, valid_key, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
        response = api_client.post(
            "/api/v1/licenses/activate",
            activation_payload(valid_key),
            format="json",
            **HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "activated"
        assert "license_id" in data
        assert "expiry_date" in data
        assert data["license_type"] == "commercial"
        assert data["days_remaining"] > 0

    def test_crea_cliente_nuevo(self, api_client, valid_key, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
        assert Client.objects.count() == 0

        api_client.post(
            "/api/v1/licenses/activate",
            activation_payload(valid_key),
            format="json",
            **HEADERS,
        )

        assert Client.objects.count() == 1
        client = Client.objects.first()
        assert client.nit == FAKE_NIT
        assert client.mac == FAKE_MAC

    def test_crea_licencia_en_db(self, api_client, valid_key, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY

        api_client.post(
            "/api/v1/licenses/activate",
            activation_payload(valid_key),
            format="json",
            **HEADERS,
        )

        assert License.objects.count() == 1
        lic = License.objects.first()
        assert lic.status == "active"
        assert lic.license_type == "commercial"

    def test_crea_audit_log(self, api_client, valid_key, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY

        api_client.post(
            "/api/v1/licenses/activate",
            activation_payload(valid_key),
            format="json",
            **HEADERS,
        )

        assert AuditLog.objects.filter(action="ACTIVATE", result="success").exists()

    def test_renovacion_expira_licencia_previa(self, api_client, valid_key, settings,
                                               existing_client, active_license):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY

        api_client.post(
            "/api/v1/licenses/activate",
            activation_payload(valid_key),
            format="json",
            **HEADERS,
        )

        active_license.refresh_from_db()
        assert active_license.status == "expired"
        assert License.objects.filter(status="active").count() == 1

    def test_clave_invalida_retorna_400(self, api_client, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
        settings.LICENSE_SECRET_KEY = "TEST_SECRET_FASE3"

        payload = activation_payload("XXXX-XXXX-XXXX-XXXX")
        response = api_client.post(
            "/api/v1/licenses/activate",
            payload,
            format="json",
            **HEADERS,
        )

        assert response.status_code == 400
        assert response.json()["error"] == "INVALID_KEY"

    def test_sin_api_key_retorna_403(self, api_client, valid_key, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY

        response = api_client.post(
            "/api/v1/licenses/activate",
            activation_payload(valid_key),
            format="json",
            # Sin header X-License-Agent-Key
        )
        assert response.status_code == 403

    def test_api_key_incorrecta_retorna_403(self, api_client, valid_key, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY

        response = api_client.post(
            "/api/v1/licenses/activate",
            activation_payload(valid_key),
            format="json",
            HTTP_X_LICENSE_AGENT_KEY="clave-incorrecta",
        )
        assert response.status_code == 403

    def test_body_incompleto_retorna_400(self, api_client, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY

        response = api_client.post(
            "/api/v1/licenses/activate",
            {"mac": FAKE_MAC},  # Faltan nit, client_name, license_key
            format="json",
            **HEADERS,
        )
        assert response.status_code == 400

    def test_audit_log_clave_invalida(self, api_client, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
        settings.LICENSE_SECRET_KEY = "TEST_SECRET_FASE3"

        api_client.post(
            "/api/v1/licenses/activate",
            activation_payload("XXXX-XXXX-XXXX-XXXX"),
            format="json",
            **HEADERS,
        )

        assert AuditLog.objects.filter(action="ACTIVATE", result="rejected").exists()


# ─────────────────────────────────────────────────────────────
#  2. ENDPOINT /validate
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestValidateEndpoint:

    def test_licencia_activa_retorna_valid_true(self, api_client, valid_key, settings,
                                                existing_client, active_license):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY

        response = api_client.post(
            "/api/v1/licenses/validate",
            {"mac": FAKE_MAC, "nit": FAKE_NIT, "license_key": valid_key},
            format="json",
            **HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["status"] == "active"
        assert data["days_remaining"] > 0

    def test_licencia_vencida_retorna_valid_false(self, api_client, valid_key, settings,
                                                   existing_client, expired_license):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY

        response = api_client.post(
            "/api/v1/licenses/validate",
            {"mac": FAKE_MAC, "nit": FAKE_NIT, "license_key": valid_key},
            format="json",
            **HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    def test_cliente_no_existe_retorna_valid_false(self, api_client, valid_key, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY

        response = api_client.post(
            "/api/v1/licenses/validate",
            {"mac": FAKE_MAC, "nit": FAKE_NIT, "license_key": valid_key},
            format="json",
            **HEADERS,
        )

        assert response.status_code == 200
        assert response.json()["valid"] is False

    def test_actualiza_last_validated_at(self, api_client, valid_key, settings,
                                          existing_client, active_license):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
        before = active_license.last_validated_at

        api_client.post(
            "/api/v1/licenses/validate",
            {"mac": FAKE_MAC, "nit": FAKE_NIT, "license_key": valid_key},
            format="json",
            **HEADERS,
        )

        active_license.refresh_from_db()
        assert active_license.last_validated_at != before

    def test_crea_audit_log_validate(self, api_client, valid_key, settings,
                                      existing_client, active_license):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY

        api_client.post(
            "/api/v1/licenses/validate",
            {"mac": FAKE_MAC, "nit": FAKE_NIT, "license_key": valid_key},
            format="json",
            **HEADERS,
        )

        assert AuditLog.objects.filter(action="VALIDATE", result="success").exists()

    def test_retorna_server_time(self, api_client, valid_key, settings,
                                  existing_client, active_license):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY

        response = api_client.post(
            "/api/v1/licenses/validate",
            {"mac": FAKE_MAC, "nit": FAKE_NIT, "license_key": valid_key},
            format="json",
            **HEADERS,
        )

        assert "server_time" in response.json()

    def test_sin_api_key_retorna_403(self, api_client, valid_key):
        response = api_client.post(
            "/api/v1/licenses/validate",
            {"mac": FAKE_MAC, "nit": FAKE_NIT, "license_key": valid_key},
            format="json",
        )
        assert response.status_code == 403


# ─────────────────────────────────────────────────────────────
#  3. ENDPOINT /trial
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTrialEndpoint:

    def test_primera_prueba_exitosa(self, api_client, valid_key, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY

        response = api_client.post(
            "/api/v1/licenses/trial",
            activation_payload(valid_key),
            format="json",
            **HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "trial_activated"
        assert data["license_type"] == "trial"
        assert data["days_remaining"] == 30

    def test_marca_trial_used_en_cliente(self, api_client, valid_key, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY

        api_client.post(
            "/api/v1/licenses/trial",
            activation_payload(valid_key),
            format="json",
            **HEADERS,
        )

        client = Client.objects.get(mac=FAKE_MAC, nit=FAKE_NIT)
        assert client.trial_used is True

    def test_segunda_prueba_retorna_409(self, api_client, valid_key, settings,
                                         existing_client):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
        existing_client.trial_used = True
        existing_client.save()

        response = api_client.post(
            "/api/v1/licenses/trial",
            activation_payload(valid_key),
            format="json",
            **HEADERS,
        )

        assert response.status_code == 409
        assert response.json()["error"] == "TRIAL_ALREADY_USED"

    def test_audit_log_trial_activado(self, api_client, valid_key, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY

        api_client.post(
            "/api/v1/licenses/trial",
            activation_payload(valid_key),
            format="json",
            **HEADERS,
        )

        assert AuditLog.objects.filter(
            action="TRIAL_ACTIVATE", result="success"
        ).exists()

    def test_audit_log_trial_rechazado(self, api_client, valid_key, settings,
                                        existing_client):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
        existing_client.trial_used = True
        existing_client.save()

        api_client.post(
            "/api/v1/licenses/trial",
            activation_payload(valid_key),
            format="json",
            **HEADERS,
        )

        assert AuditLog.objects.filter(
            action="TRIAL_ACTIVATE", result="rejected"
        ).exists()

    def test_clave_invalida_retorna_400(self, api_client, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
        settings.LICENSE_SECRET_KEY = "TEST_SECRET_FASE3"

        payload = activation_payload("XXXX-XXXX-XXXX-XXXX")
        response = api_client.post(
            "/api/v1/licenses/trial",
            payload,
            format="json",
            **HEADERS,
        )
        assert response.status_code == 400

    def test_licencia_trial_dura_30_dias(self, api_client, valid_key, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
        settings.LICENSE_TRIAL_DAYS = 30

        api_client.post(
            "/api/v1/licenses/trial",
            activation_payload(valid_key),
            format="json",
            **HEADERS,
        )

        lic = License.objects.get(license_type="trial")
        delta = lic.expiry_date - timezone.now()
        # Permite 1 segundo de margen
        assert 29 <= delta.days <= 30


# ─────────────────────────────────────────────────────────────
#  4. MODELOS
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestModels:

    def test_client_str(self):
        c = Client(name="Empresa X", nit="900000001-0")
        assert "Empresa X" in str(c)
        assert "900000001-0" in str(c)

    def test_license_is_valid(self, existing_client):
        lic = License.objects.create(
            client=existing_client,
            license_type="commercial",
            status="active",
            expiry_date=timezone.now() + timedelta(days=100),
        )
        assert lic.is_valid is True
        assert lic.days_remaining > 0

    def test_license_vencida_is_not_valid(self, existing_client):
        lic = License.objects.create(
            client=existing_client,
            license_type="commercial",
            status="expired",
            expiry_date=timezone.now() - timedelta(days=1),
        )
        assert lic.is_valid is False
        assert lic.days_remaining == 0

    def test_license_revoke(self, existing_client, active_license):
        from django.contrib.auth.models import User
        user = User.objects.create_user("admin_test", password="x")
        active_license.revoke(user=user, note="Test revocación")

        active_license.refresh_from_db()
        assert active_license.status == "revoked"
        assert active_license.revoked_by == user
        assert "Test revocación" in active_license.notes

    def test_audit_log_helper(self, existing_client, active_license):
        log = AuditLog.log(
            action="VALIDATE",
            result="success",
            license=active_license,
            client=existing_client,
            ip="192.168.1.1",
            detail={"test": True},
        )
        assert log.pk is not None
        assert log.action == "VALIDATE"
        assert log.ip_address == "192.168.1.1"

    def test_client_active_license(self, existing_client, active_license):
        assert existing_client.active_license == active_license

    def test_client_active_license_none_si_vencida(self, existing_client, expired_license):
        assert existing_client.active_license is None


# ─────────────────────────────────────────────────────────────
#  5. VALIDATORS
# ─────────────────────────────────────────────────────────────

class TestValidators:

    def test_generate_key_determinístico(self, settings):
        settings.LICENSE_SECRET_KEY = "TEST_SECRET"
        k1 = generate_license_key(FAKE_MAC, FAKE_NIT)
        k2 = generate_license_key(FAKE_MAC, FAKE_NIT)
        assert k1 == k2

    def test_generate_key_formato(self, settings):
        settings.LICENSE_SECRET_KEY = "TEST_SECRET"
        key = generate_license_key(FAKE_MAC, FAKE_NIT)
        parts = key.split("-")
        assert len(parts) == 4
        assert all(len(p) == 4 for p in parts)

    def test_verify_key_correcta(self, settings):
        from licenses.validators import verify_license_key
        settings.LICENSE_SECRET_KEY = "TEST_SECRET"
        key = generate_license_key(FAKE_MAC, FAKE_NIT)
        assert verify_license_key(FAKE_MAC, FAKE_NIT, key) is True

    def test_verify_key_incorrecta(self, settings):
        from licenses.validators import verify_license_key
        settings.LICENSE_SECRET_KEY = "TEST_SECRET"
        assert verify_license_key(FAKE_MAC, FAKE_NIT, "XXXX-XXXX-XXXX-XXXX") is False

    def test_mac_normalizada_misma_clave(self, settings):
        settings.LICENSE_SECRET_KEY = "TEST_SECRET"
        k1 = generate_license_key("AABBCCDDEEFF", FAKE_NIT)
        k2 = generate_license_key("AA:BB:CC:DD:EE:FF", FAKE_NIT)
        k3 = generate_license_key("AA-BB-CC-DD-EE-FF", FAKE_NIT)
        assert k1 == k2 == k3

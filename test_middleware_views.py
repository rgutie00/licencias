"""
test_middleware_views.py — Fase 2
Tests de integración del LicenseMiddleware y las vistas.

Cómo ejecutar:
    pip install pytest pytest-django psutil httpx cryptography
    pytest test_middleware_views.py -v

Todos los tests usan mock del LicenseEngine — sin red, sin archivos reales.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client, RequestFactory

from license_system.license_engine import LicenseResult
from license_system.license_middleware import LicenseMiddleware

# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────

def make_result(status, days=365, license_type="commercial"):
    """Crea un LicenseResult con valores por defecto."""
    expiry = datetime.now(timezone.utc) + timedelta(days=days)
    return LicenseResult(
        status=status,
        expiry_date=expiry if status == "VALID" else None,
        days_remaining=days if status == "VALID" else 0,
        license_type=license_type,
    )


def mock_engine(status, days=365):
    """Crea un mock del engine que retorna el status dado."""
    engine = MagicMock()
    engine.validate.return_value = make_result(status, days)
    engine.get_server_mac.return_value = "AABBCCDDEEFF"
    engine.generate_key.return_value = "A3KL-7PQR-XZ2W-M9BN"
    return engine


# ─────────────────────────────────────────────────────────────
#  1. MIDDLEWARE — BLOQUEOS Y PERMISOS
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestMiddlewareBlocking:

    def test_sin_licencia_redirige_a_activate(self):
        """Sin licencia, cualquier ruta protegida → /license/activate/"""
        with patch("license_system.license_middleware.get_engine",
                   return_value=mock_engine("NO_LICENSE")):
            client = Client()
            response = client.get("/dashboard/")

        assert response.status_code == 302
        assert response["Location"] == "/license/activate/"

    def test_licencia_valida_pasa(self):
        """Con licencia válida, el request llega a la vista."""
        with patch("license_system.license_middleware.get_engine",
                   return_value=mock_engine("VALID")):
            client = Client()
            response = client.get("/dashboard/")

        assert response.status_code == 200
        assert b"OK" in response.content

    def test_licencia_vencida_redirige_a_expired(self):
        with patch("license_system.license_middleware.get_engine",
                   return_value=mock_engine("EXPIRED")):
            client = Client()
            response = client.get("/dashboard/")

        assert response.status_code == 302
        assert response["Location"] == "/license/expired/"

    def test_token_manipulado_redirige_con_reason(self):
        engine = mock_engine("TAMPERED")
        with patch("license_system.license_middleware.get_engine",
                   return_value=engine):
            client = Client()
            response = client.get("/dashboard/")

        assert response.status_code == 302
        assert "reason=tampered" in response["Location"]
        engine.delete_token.assert_called_once()

    def test_clock_rollback_redirige_con_reason(self):
        engine = mock_engine("CLOCK_ROLLBACK")
        with patch("license_system.license_middleware.get_engine",
                   return_value=engine):
            client = Client()
            response = client.get("/dashboard/")

        assert response.status_code == 302
        assert "reason=clock" in response["Location"]
        engine.delete_token.assert_called_once()

    def test_api_protegida_sin_licencia(self):
        """Las rutas /api/ también están protegidas."""
        with patch("license_system.license_middleware.get_engine",
                   return_value=mock_engine("NO_LICENSE")):
            client = Client()
            response = client.get("/api/data/")

        assert response.status_code == 302
        assert response["Location"] == "/license/activate/"

    def test_login_protegido_sin_licencia(self):
        """/accounts/login/ también está protegida — sin licencia no hay login."""
        with patch("license_system.license_middleware.get_engine",
                   return_value=mock_engine("NO_LICENSE")):
            client = Client()
            response = client.get("/accounts/login/")

        assert response.status_code == 302
        assert response["Location"] == "/license/activate/"


# ─────────────────────────────────────────────────────────────
#  2. MIDDLEWARE — RUTAS EXENTAS
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestMiddlewareExemptRoutes:

    def test_license_activate_exenta(self):
        """/license/ nunca requiere licencia válida (evita bucle infinito)."""
        with patch("license_system.license_middleware.get_engine",
                   return_value=mock_engine("NO_LICENSE")):
            client = Client()
            response = client.get("/license/activate/")

        # Llega a la vista (no redirige a sí mismo)
        assert response.status_code == 200

    def test_static_exento(self):
        with patch("license_system.license_middleware.get_engine",
                   return_value=mock_engine("NO_LICENSE")) as m:
            client = Client()
            # /static/ no existe en test pero el middleware lo deja pasar
            rf = RequestFactory()
            request = rf.get("/static/css/main.css")
            middleware = LicenseMiddleware(lambda r: MagicMock(status_code=200))
            middleware(request)

        # El engine no debe ser llamado para rutas estáticas
        m.return_value.validate.assert_not_called()

    def test_favicon_exento(self):
        rf = RequestFactory()
        request = rf.get("/favicon.ico")
        called = []

        def get_response(r):
            called.append(True)
            return MagicMock(status_code=200)

        with patch("license_system.license_middleware.get_engine") as mock_get:
            middleware = LicenseMiddleware(get_response)
            middleware(request)

        mock_get.assert_not_called()
        assert called, "get_response no fue llamado para ruta exenta"


# ─────────────────────────────────────────────────────────────
#  3. MIDDLEWARE — request.license adjuntado
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestMiddlewareLicenseAttachment:

    def test_request_license_disponible(self):
        """Con licencia válida, request.license está disponible en la vista."""
        with patch("license_system.license_middleware.get_engine",
                   return_value=mock_engine("VALID", days=100)):
            client = Client()
            response = client.get("/dashboard/")

        assert response.status_code == 200
        assert b"license=VALID" in response.content

    def test_warning_pocos_dias(self):
        """Con ≤7 días restantes se adjunta request.license_warning."""
        engine = mock_engine("VALID", days=3)
        request_received = {}

        def capture_view(request):
            from django.http import HttpResponse
            request_received["warning"] = getattr(request, "license_warning", None)
            return HttpResponse("OK")

        rf = RequestFactory()
        request = rf.get("/dashboard/")

        with patch("license_system.license_middleware.get_engine", return_value=engine):
            middleware = LicenseMiddleware(capture_view)
            middleware(request)

        assert request_received["warning"] is not None
        assert "3" in request_received["warning"]

    def test_sin_warning_dias_suficientes(self):
        """Con más de 7 días, no debe haber license_warning."""
        engine = mock_engine("VALID", days=30)
        request_received = {}

        def capture_view(request):
            from django.http import HttpResponse
            request_received["warning"] = getattr(request, "license_warning", None)
            return HttpResponse("OK")

        rf = RequestFactory()
        request = rf.get("/dashboard/")

        with patch("license_system.license_middleware.get_engine", return_value=engine):
            middleware = LicenseMiddleware(capture_view)
            middleware(request)

        assert request_received["warning"] is None


# ─────────────────────────────────────────────────────────────
#  4. VISTA ACTIVATE — GET
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestActivateViewGet:

    def test_get_muestra_formulario(self):
        engine = mock_engine("NO_LICENSE")
        with patch("license_system.license_middleware.get_engine", return_value=engine):
            with patch("license_system.views.get_engine", return_value=engine):
                client = Client()
                response = client.get("/license/activate/")

        assert response.status_code == 200
        assert b"NIT" in response.content or b"nit" in response.content

    def test_get_muestra_reason_tampered(self):
        engine = mock_engine("NO_LICENSE")
        with patch("license_system.license_middleware.get_engine", return_value=engine):
            with patch("license_system.views.get_engine", return_value=engine):
                client = Client()
                response = client.get("/license/activate/?reason=tampered")

        assert response.status_code == 200
        assert b"manipulado" in response.content.lower() or b"corrupto" in response.content.lower()

    def test_get_muestra_reason_clock(self):
        engine = mock_engine("NO_LICENSE")
        with patch("license_system.license_middleware.get_engine", return_value=engine):
            with patch("license_system.views.get_engine", return_value=engine):
                client = Client()
                response = client.get("/license/activate/?reason=clock")

        assert response.status_code == 200
        assert b"reloj" in response.content.lower()


# ─────────────────────────────────────────────────────────────
#  5. VISTA ACTIVATE — POST
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestActivateViewPost:

    def _make_engine_with_server(self, status="NO_LICENSE"):
        """Engine con servidor configurado para tests de POST."""
        engine = mock_engine(status)
        engine.get_server_mac.return_value = "AABBCCDDEEFF"
        engine.generate_key.return_value = "A3KL-7PQR-XZ2W-M9BN"
        return engine

    def test_post_sin_nit_retorna_error(self):
        engine = self._make_engine_with_server()
        with patch("license_system.license_middleware.get_engine", return_value=engine):
            with patch("license_system.views.get_engine", return_value=engine):
                client = Client()
                response = client.post("/license/activate/", {
                    "client_name": "Empresa Test",
                    "license_type": "commercial",
                })

        assert response.status_code == 200
        assert b"NIT es obligatorio" in response.content

    def test_post_sin_nombre_retorna_error(self):
        engine = self._make_engine_with_server()
        with patch("license_system.license_middleware.get_engine", return_value=engine):
            with patch("license_system.views.get_engine", return_value=engine):
                client = Client()
                response = client.post("/license/activate/", {
                    "nit": "900123456-7",
                    "license_type": "commercial",
                })

        assert response.status_code == 200
        assert b"nombre" in response.content.lower()

    def test_post_sin_servidor_configurado_muestra_error(self):
        """Sin LICENSE_SERVER_URL debe mostrar error de configuración."""
        from django.test import override_settings
        engine = self._make_engine_with_server()

        with override_settings(LICENSE_SERVER_URL=""):
            with patch("license_system.license_middleware.get_engine", return_value=engine):
                with patch("license_system.views.get_engine", return_value=engine):
                    client = Client()
                    response = client.post("/license/activate/", {
                        "nit": "900123456-7",
                        "client_name": "Empresa Test",
                        "license_type": "commercial",
                    })

        assert response.status_code == 200
        assert b"no est" in response.content.lower()

    def test_post_servidor_ok_redirige_a_success(self):
        """Servidor responde 200 → redirect a /license/success/"""
        from unittest.mock import patch as p
        import httpx

        engine = self._make_engine_with_server()
        server_response = MagicMock()
        server_response.status_code = 200
        server_response.json.return_value = {
            "expiry_date": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "license_type": "commercial",
            "server_time": datetime.now(timezone.utc).isoformat(),
        }

        from django.test import override_settings
        with override_settings(LICENSE_SERVER_URL="https://test.server.com/api/v1"):
            with patch("license_system.license_middleware.get_engine", return_value=engine):
                with patch("license_system.views.get_engine", return_value=engine):
                    with patch("license_system.views.httpx.post", return_value=server_response):
                        client = Client()
                        response = client.post("/license/activate/", {
                            "nit": "900123456-7",
                            "client_name": "Empresa Test",
                            "license_type": "commercial",
                        })

        assert response.status_code == 302
        assert response["Location"] == "/license/success/"
        engine.activate_from_response.assert_called_once()

    def test_post_servidor_409_trial_ya_usado(self):
        """Servidor responde 409 → mensaje de prueba ya usada."""
        engine = self._make_engine_with_server()
        server_response = MagicMock()
        server_response.status_code = 409

        from django.test import override_settings
        with override_settings(LICENSE_SERVER_URL="https://test.server.com/api/v1"):
            with patch("license_system.license_middleware.get_engine", return_value=engine):
                with patch("license_system.views.get_engine", return_value=engine):
                    with patch("license_system.views.httpx.post", return_value=server_response):
                        client = Client()
                        response = client.post("/license/activate/", {
                            "nit": "900123456-7",
                            "client_name": "Empresa Test",
                            "license_type": "trial",
                        })

        assert response.status_code == 200
        assert b"prueba" in response.content.lower()

    def test_post_sin_conexion_muestra_error(self):
        """Timeout de red → mensaje de error de conexión."""
        import httpx as _httpx
        engine = self._make_engine_with_server()

        from django.test import override_settings
        with override_settings(LICENSE_SERVER_URL="https://test.server.com/api/v1"):
            with patch("license_system.license_middleware.get_engine", return_value=engine):
                with patch("license_system.views.get_engine", return_value=engine):
                    with patch("license_system.views.httpx.post",
                               side_effect=_httpx.ConnectError("timeout")):
                        client = Client()
                        response = client.post("/license/activate/", {
                            "nit": "900123456-7",
                            "client_name": "Empresa Test",
                            "license_type": "commercial",
                        })

        assert response.status_code == 200
        assert b"conexi" in response.content.lower()


# ─────────────────────────────────────────────────────────────
#  6. VISTA EXPIRED
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestExpiredView:

    def test_muestra_pantalla_de_vencimiento(self):
        engine = mock_engine("NO_LICENSE")
        with patch("license_system.license_middleware.get_engine", return_value=engine):
            client = Client()
            response = client.get("/license/expired/")

        assert response.status_code == 200
        assert b"Vencida" in response.content or b"vencida" in response.content.lower()

    def test_tiene_link_a_activate(self):
        engine = mock_engine("NO_LICENSE")
        with patch("license_system.license_middleware.get_engine", return_value=engine):
            client = Client()
            response = client.get("/license/expired/")

        assert b"/license/activate/" in response.content


# ─────────────────────────────────────────────────────────────
#  7. VISTA SUCCESS
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSuccessView:

    def test_muestra_confirmacion(self):
        engine = mock_engine("NO_LICENSE")
        with patch("license_system.license_middleware.get_engine", return_value=engine):
            client = Client()
            response = client.get("/license/success/")

        assert response.status_code == 200
        assert b"Activada" in response.content or b"activada" in response.content.lower()

    def test_tiene_link_al_login(self):
        engine = mock_engine("NO_LICENSE")
        with patch("license_system.license_middleware.get_engine", return_value=engine):
            client = Client()
            response = client.get("/license/success/")

        assert b"/accounts/login/" in response.content


# ─────────────────────────────────────────────────────────────
#  8. MIDDLEWARE — IP EXTRACTION
# ─────────────────────────────────────────────────────────────

class TestMiddlewareIPExtraction:

    def test_ip_directa(self):
        rf = RequestFactory()
        request = rf.get("/dashboard/")
        request.META["REMOTE_ADDR"] = "192.168.1.100"
        ip = LicenseMiddleware._get_ip(request)
        assert ip == "192.168.1.100"

    def test_ip_con_proxy(self):
        rf = RequestFactory()
        request = rf.get("/dashboard/")
        request.META["HTTP_X_FORWARDED_FOR"] = "10.0.0.5, 172.16.0.1"
        ip = LicenseMiddleware._get_ip(request)
        assert ip == "10.0.0.5"

    def test_ip_sin_meta(self):
        rf = RequestFactory()
        request = rf.get("/dashboard/")
        request.META.pop("REMOTE_ADDR", None)
        ip = LicenseMiddleware._get_ip(request)
        assert ip == "unknown"

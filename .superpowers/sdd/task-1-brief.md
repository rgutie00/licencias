# Task 1 Brief — Agregar TestValidateOnline

## Contexto
Estás trabajando en `C:\desarrollos\licencias\`. Este es el motor criptográfico de un sistema de licencias Django (Fase 1). La implementación en `license_engine.py` ya existe y está completa. Los tests en `test_license_engine.py` tienen 52 tests que pasan al 100%, pero la cobertura es 81%. Tu trabajo es agregar una clase de tests que cubra `validate_online()` (líneas 262-310).

## Tu única tarea
Agregar la clase `TestValidateOnline` al final de `test_license_engine.py`, después de la clase `TestLicenseResult`.

## Código exacto a agregar

Al final del archivo `test_license_engine.py` (después de la última clase `TestLicenseResult`), agregar exactamente:

```python
# ─────────────────────────────────────────────────────────────
#  10. VALIDACIÓN ONLINE (httpx mocks)
# ─────────────────────────────────────────────────────────────

class TestValidateOnline:
    """Prueba validate_online() mockeando httpx.post — sin red real."""

    SERVER = "http://licencias.test"

    @pytest.fixture
    def online_engine(self, tmp_path):
        return LicenseEngine(
            secret_key=SECRET,
            token_path=str(tmp_path / "license.tok"),
            server_url=self.SERVER,
            api_key="test-api-key",
            max_offline_days=30,
        )

    def _mock_response(self, status_code: int, body: dict):
        """Helper: crea un mock de httpx.Response."""
        mock = MagicMock()
        mock.status_code = status_code
        mock.json.return_value = body
        return mock

    def test_servidor_responde_200_valido(self, online_engine):
        expiry = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        body = {
            "expiry_date": expiry,
            "license_type": "commercial",
            "server_time": datetime.now(timezone.utc).isoformat(),
        }
        with patch("httpx.post", return_value=self._mock_response(200, body)):
            result = online_engine.validate_online(FAKE_MAC, "XXXX-XXXX-XXXX-XXXX", FAKE_NIT)

        assert result is not None
        assert result.status == "VALID"
        assert result.days_remaining > 0
        assert result.license_type == "commercial"

    def test_servidor_responde_402_vencida(self, online_engine):
        with patch("httpx.post", return_value=self._mock_response(402, {})):
            result = online_engine.validate_online(FAKE_MAC, "XXXX-XXXX-XXXX-XXXX", FAKE_NIT)

        assert result is not None
        assert result.status == "EXPIRED"
        assert "vencida" in result.message.lower()

    def test_servidor_responde_403_revocada(self, online_engine):
        with patch("httpx.post", return_value=self._mock_response(403, {})):
            result = online_engine.validate_online(FAKE_MAC, "XXXX-XXXX-XXXX-XXXX", FAKE_NIT)

        assert result is not None
        assert result.status == "EXPIRED"
        assert "revocada" in result.message.lower()

    def test_servidor_responde_500_desconocido(self, online_engine):
        with patch("httpx.post", return_value=self._mock_response(500, {})):
            result = online_engine.validate_online(FAKE_MAC, "XXXX-XXXX-XXXX-XXXX", FAKE_NIT)

        assert result is not None
        assert result.status == "EXPIRED"
        assert "500" in result.message

    def test_timeout_retorna_none(self, online_engine):
        import httpx as httpx_lib
        with patch("httpx.post", side_effect=httpx_lib.TimeoutException("timeout")):
            result = online_engine.validate_online(FAKE_MAC, "XXXX-XXXX-XXXX-XXXX", FAKE_NIT)

        assert result is None  # Fallback a offline

    def test_connect_error_retorna_none(self, online_engine):
        import httpx as httpx_lib
        with patch("httpx.post", side_effect=httpx_lib.ConnectError("sin red")):
            result = online_engine.validate_online(FAKE_MAC, "XXXX-XXXX-XXXX-XXXX", FAKE_NIT)

        assert result is None

    def test_sin_server_url_retorna_none(self, tmp_path):
        engine_sin_url = LicenseEngine(
            secret_key=SECRET,
            token_path=str(tmp_path / "license.tok"),
            server_url="",  # Sin URL → siempre None
        )
        result = engine_sin_url.validate_online(FAKE_MAC, "XXXX-XXXX-XXXX-XXXX", FAKE_NIT)
        assert result is None
```

## Verificación
Después de agregar el código ejecutar:
```
cd C:\desarrollos\licencias
python -m pytest test_license_engine.py::TestValidateOnline -v
```
Resultado esperado: 7 tests PASSED.

Luego ejecutar la suite completa:
```
python -m pytest test_license_engine.py -v
```
Resultado esperado: 59 tests PASSED.

## Commit
```
git add test_license_engine.py
git commit -m "test(fase1): agregar cobertura de validate_online con mocks de httpx"
```

## Reporte
Escribir el resultado en `.superpowers\sdd\task-1-report.md` con:
- Status: DONE / BLOCKED / NEEDS_CONTEXT
- Tests ejecutados y resultado
- Hash del commit

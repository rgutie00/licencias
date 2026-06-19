# Fase 1 — Motor Criptográfico: Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completar y certificar la Fase 1 del motor criptográfico llevando la cobertura de tests de 81% a ≥ 95% y consolidando la estructura de archivos del paquete.

**Architecture:** `license_engine.py` es Python puro, independiente de Django. Recibe configuración como parámetros del constructor. Los tests usan `pytest` con `tmp_path` para archivos temporales y mocks de `httpx` / `psutil` para eliminar dependencias externas.

**Tech Stack:** Python 3.10+, cryptography 42, psutil 5.9, httpx 0.27, pytest 8.2, pytest-cov 5.0

## Estado Actual (Pre-plan)

```
52/52 tests pasan — cobertura 81%

Brechas identificadas:
  license_engine.py:125-135  → get_server_mac() lógica interna de filtrado
  license_engine.py:262-310  → validate_online() bloque httpx (respuestas 200/402/403/otros)
  license_engine.py:339-340  → validate_offline() handler de last_online_check malformado
```

## Estructura de Archivos

```
C:\desarrollos\licencias\
  license_engine.py              ← implementación completa (NO modificar)
  test_license_engine.py         ← 52 tests existentes (AMPLIAR con nuevas clases)
  license_system\
    license_engine.py            ← copia idéntica para el paquete Django
    engine_factory.py            ← singleton Django (importación relativa correcta aquí)
  engine_factory.py              ← versión raíz con importación relativa rota (CORREGIR)
  requirements_fase1.txt         ← completo
  docs\superpowers\plans\
    2026-06-19-fase1-motor-criptografico.md   ← este archivo
```

**Archivos a crear/modificar:**
- Modify: `test_license_engine.py` — agregar 3 clases de test (Tasks 1-3)
- Modify: `engine_factory.py` (raíz) — corregir importación relativa rota (Task 4)

## Global Constraints

- Python 3.10+ — usar `X | Y` para tipos union (no `Optional[X]`)
- Sin imports de Django en `license_engine.py` — permanece independiente
- Todos los tests deben pasar sin red, sin Django, sin archivos reales
- `pytest test_license_engine.py -v` como único comando de verificación
- Commits frecuentes por tarea completada

---

### Task 1: Cobertura de `validate_online()` — líneas 262-310

**Files:**
- Modify: `test_license_engine.py` — agregar clase `TestValidateOnline`

**Interfaces:**
- Consumes: `LicenseEngine.validate_online(mac: str, key: str, nit: str) -> LicenseResult | None`
- Produces: cobertura de las líneas 262-310 de `license_engine.py`

- [ ] **Paso 1: Agregar clase TestValidateOnline al final de `test_license_engine.py`**

Agregar después de la clase `TestLicenseResult` (última clase en el archivo):

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

- [ ] **Paso 2: Ejecutar solo los nuevos tests para verificar que fallan (código ya existe)**

```
pytest test_license_engine.py::TestValidateOnline -v
```

Resultado esperado: **7 PASSED** (el código ya existe, los tests solo añaden cobertura al flujo real de httpx)

- [ ] **Paso 3: Ejecutar suite completa y medir cobertura**

```
pytest test_license_engine.py --cov=license_engine --cov-report=term-missing -v
```

Resultado esperado: cobertura de `262-310` eliminada de la lista de brechas, total ≥ 87%.

- [ ] **Paso 4: Commit**

```
git add test_license_engine.py
git commit -m "test(fase1): agregar cobertura de validate_online con mocks de httpx"
```

---

### Task 2: Cobertura de `validate_offline()` — líneas 339-340

**Files:**
- Modify: `test_license_engine.py` — agregar método a `TestValidateOffline`

**Interfaces:**
- Consumes: `LicenseEngine.validate_offline(token: dict) -> LicenseResult`
- La brecha está en el `except ValueError` cuando `last_online_check` contiene un string no parseable como ISO datetime.

- [ ] **Paso 1: Agregar test al final de la clase `TestValidateOffline` existente**

Agregar dentro de `class TestValidateOffline:` después del último método (`test_license_type_trial`):

```python
    def test_last_check_malformado_usa_fallback(self, engine):
        """last_online_check con formato inválido → usa 2000-01-01 como fallback.
        El sistema no debe explotar; debe continuar con la validación normal."""
        expiry = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        token = {
            "expiry": expiry,
            "last_online_check": "esto-no-es-una-fecha-valida",
            "license_type": "commercial",
        }
        result = engine.validate_offline(token)
        # Con last_check = 2000-01-01, offline_days ≈ 9000 > 30 → EXPIRED
        assert result.status == "EXPIRED"
        assert "offline" in result.message.lower()
```

- [ ] **Paso 2: Ejecutar el nuevo test**

```
pytest test_license_engine.py::TestValidateOffline::test_last_check_malformado_usa_fallback -v
```

Resultado esperado: **PASSED**

- [ ] **Paso 3: Ejecutar suite con cobertura**

```
pytest test_license_engine.py --cov=license_engine --cov-report=term-missing -v
```

Resultado esperado: líneas `339-340` eliminadas de las brechas, total ≥ 89%.

- [ ] **Paso 4: Commit**

```
git add test_license_engine.py
git commit -m "test(fase1): cubrir handler de last_online_check malformado"
```

---

### Task 3: Cobertura de `get_server_mac()` — líneas 125-135

**Files:**
- Modify: `test_license_engine.py` — agregar clase `TestGetServerMac`

**Interfaces:**
- Consumes: `LicenseEngine.get_server_mac() -> str` y `LicenseEngine._normalize_mac(raw: str) -> str`
- La brecha está en el bucle de filtrado de interfaces (loopback, MAC nula, AF_LINK)
- Producir cobertura sin usar psutil real (mock de `psutil.net_if_addrs`)

- [ ] **Paso 1: Agregar clase TestGetServerMac después de TestValidateOnline**

```python
# ─────────────────────────────────────────────────────────────
#  11. GET SERVER MAC (psutil mock)
# ─────────────────────────────────────────────────────────────

class TestGetServerMac:
    """Prueba get_server_mac() mockeando psutil.net_if_addrs."""

    def _addr(self, family, address):
        """Crea un mock de snic (psutil address namedtuple)."""
        a = MagicMock()
        a.family = family
        a.address = address
        return a

    def test_retorna_primera_mac_valida(self, engine):
        fake_addrs = {
            "eth0": [self._addr(psutil.AF_LINK, "AA:BB:CC:DD:EE:FF")],
        }
        with patch("psutil.net_if_addrs", return_value=fake_addrs):
            mac = engine.get_server_mac()
        assert mac == "AABBCCDDEEFF"

    def test_ignora_loopback(self, engine):
        fake_addrs = {
            "lo":   [self._addr(psutil.AF_LINK, "00:00:00:00:00:00")],
            "eth0": [self._addr(psutil.AF_LINK, "AA:BB:CC:DD:EE:FF")],
        }
        with patch("psutil.net_if_addrs", return_value=fake_addrs):
            mac = engine.get_server_mac()
        assert mac == "AABBCCDDEEFF"

    def test_ignora_mac_nula(self, engine):
        fake_addrs = {
            "eth0": [
                self._addr(psutil.AF_LINK, "00:00:00:00:00:00"),
                self._addr(psutil.AF_LINK, "AA:BB:CC:DD:EE:FF"),
            ],
        }
        with patch("psutil.net_if_addrs", return_value=fake_addrs):
            mac = engine.get_server_mac()
        assert mac == "AABBCCDDEEFF"

    def test_ignora_familia_no_link(self, engine):
        import socket
        fake_addrs = {
            "eth0": [
                self._addr(socket.AF_INET, "192.168.1.1"),   # IP, no MAC
                self._addr(psutil.AF_LINK, "AA:BB:CC:DD:EE:FF"),
            ],
        }
        with patch("psutil.net_if_addrs", return_value=fake_addrs):
            mac = engine.get_server_mac()
        assert mac == "AABBCCDDEEFF"

    def test_sin_interfaces_validas_lanza_error(self, engine):
        fake_addrs = {
            "lo": [self._addr(psutil.AF_LINK, "00:00:00:00:00:00")],
        }
        with patch("psutil.net_if_addrs", return_value=fake_addrs):
            with pytest.raises(RuntimeError, match="interfaz de red"):
                engine.get_server_mac()

    def test_sin_interfaces_lanza_error(self, engine):
        with patch("psutil.net_if_addrs", return_value={}):
            with pytest.raises(RuntimeError):
                engine.get_server_mac()
```

Agregar también el import de `psutil` al inicio del archivo (después de los imports existentes):

```python
import psutil
```

- [ ] **Paso 2: Ejecutar los nuevos tests**

```
pytest test_license_engine.py::TestGetServerMac -v
```

Resultado esperado: **6 PASSED**

- [ ] **Paso 3: Ejecutar suite completa con cobertura**

```
pytest test_license_engine.py --cov=license_engine --cov-report=term-missing -v
```

Resultado esperado: total ≥ 95%, brechas 125-135 eliminadas.

- [ ] **Paso 4: Commit**

```
git add test_license_engine.py
git commit -m "test(fase1): agregar cobertura de get_server_mac con mocks de psutil"
```

---

### Task 4: Corregir `engine_factory.py` en la raíz

**Files:**
- Modify: `engine_factory.py` (raíz, no `license_system/engine_factory.py`)

**Interfaces:**
- El archivo raíz usa `from .license_engine import LicenseEngine` (importación relativa)
- Una importación relativa fuera de un paquete lanza `ImportError: attempted relative import with no known parent package`
- El archivo correcto para Django está en `license_system/engine_factory.py` (no tocar)
- El archivo raíz es para contextos standalone (tests de integración, scripts CLI)

- [ ] **Paso 1: Verificar que la importación relativa rompe en contexto standalone**

```
python -c "from engine_factory import get_engine"
```

Resultado esperado: `ImportError: attempted relative import with no known parent package`

- [ ] **Paso 2: Editar `engine_factory.py` (raíz) — cambiar importación relativa por absoluta**

Cambiar la línea:
```python
from .license_engine import LicenseEngine
```

Por:
```python
from license_engine import LicenseEngine
```

El archivo `license_system/engine_factory.py` NO debe modificarse (su importación relativa es correcta dentro del paquete Django).

- [ ] **Paso 3: Verificar que la importación funciona desde la raíz**

```
python -c "from engine_factory import get_engine; print('OK')"
```

Resultado esperado: error de Django settings (no de importación). La clase se importa correctamente pero `get_engine()` necesita Django configurado. El test es solo verificar que no lanza `ImportError`.

Salida esperada:
```
django.core.exceptions.ImproperlyConfigured: Requested setting LICENSE_SECRET_KEY...
```
o similar (error de Django, no de importación).

- [ ] **Paso 4: Ejecutar suite completa para confirmar que nada se rompió**

```
pytest test_license_engine.py -v
```

Resultado esperado: **≥ 59 passed** (52 originales + 7 nuevos de Task 1 + 1 de Task 2 + 6 de Task 3).

- [ ] **Paso 5: Commit**

```
git add engine_factory.py
git commit -m "fix(fase1): corregir importación relativa en engine_factory.py raíz"
```

---

### Task 5: Verificación final de Fase 1

**Files:**
- Read: `test_license_engine.py` (verificación)
- Read: `license_engine.py` (verificación)

**Interfaces:**
- Produce: reporte de cobertura ≥ 95% y lista de archivos entregados

- [ ] **Paso 1: Ejecutar suite completa con reporte de cobertura**

```
pytest test_license_engine.py -v --cov=license_engine --cov-report=term-missing --tb=short
```

Resultado esperado:
```
≥ 59 passed
Coverage: ≥ 95%
Missing: solo líneas de logger.debug (aceptable)
```

- [ ] **Paso 2: Verificar requirements_fase1.txt está completo**

```
pip install -r requirements_fase1.txt --dry-run 2>&1 | tail -5
```

No debe haber errores de dependencias faltantes.

- [ ] **Paso 3: Confirmar que license_engine.py no tiene imports de Django**

```
python -c "
import ast, pathlib
tree = ast.parse(pathlib.Path('license_engine.py').read_text())
django_imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) and hasattr(n, 'module') and n.module and 'django' in n.module]
assert not django_imports, f'Django imports encontrados: {django_imports}'
print('OK — license_engine.py no depende de Django')
"
```

Resultado esperado: `OK — license_engine.py no depende de Django`

- [ ] **Paso 4: Commit final de Fase 1**

```
git add .
git commit -m "feat(fase1): motor criptografico completo — cobertura ≥95%, independiente de Django"
```

---

## Resumen de entregables de Fase 1

| Archivo | Estado | Tests |
|---|---|---|
| `license_engine.py` | Completo | 52 → ≥59 tests |
| `test_license_engine.py` | Ampliar con Tasks 1-3 | ≥59 tests, ≥95% cobertura |
| `engine_factory.py` (raíz) | Corregir importación | N/A |
| `requirements_fase1.txt` | Completo | N/A |

**Punto de integración con Fase 2:** `engine_factory.py` en `license_system/` importa `LicenseEngine` via importación relativa (`from .license_engine import LicenseEngine`) y lo conecta con `settings.py` de Django. Fase 2 no requiere cambios en `license_engine.py`.

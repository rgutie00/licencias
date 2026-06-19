# Task 3 Brief — Agregar TestGetServerMac

## Contexto
Estás trabajando en `C:\desarrollos\licencias\`. Los tests de `test_license_engine.py` ahora tienen 60 tests (todos pasan). Queda la última brecha de cobertura: líneas 125-135 de `license_engine.py` — el bucle interno de `get_server_mac()` que filtra interfaces de red.

## Tu única tarea
Agregar la clase `TestGetServerMac` y el import de `psutil` al archivo `test_license_engine.py`.

## Paso 1: Agregar import de psutil

Al inicio del archivo `test_license_engine.py`, después de la línea `import pytest`, agregar:

```python
import psutil
```

Busca el bloque de imports existente (aproximadamente líneas 1-20). El import de psutil va junto a los demás imports de librerías.

## Paso 2: Agregar la clase TestGetServerMac al final del archivo

Agregar después de la clase `TestValidateOnline` (al final del archivo):

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

## Verificación
```
cd C:\desarrollos\licencias
python -m pytest test_license_engine.py::TestGetServerMac -v
```
Resultado esperado: 6 tests PASSED.

Luego:
```
python -m pytest test_license_engine.py -v
```
Resultado esperado: 66 tests PASSED.

Luego medir cobertura:
```
python -m pytest test_license_engine.py --cov=license_engine --cov-report=term-missing
```
Resultado esperado: cobertura ≥ 92% (líneas 125-135 ya no aparecen como brecha).

## Commit
```
git add test_license_engine.py
git commit -m "test(fase1): agregar cobertura de get_server_mac con mocks de psutil"
```

## Reporte
Escribe en `.superpowers\sdd\task-3-report.md`:
```
Status: DONE
Tests: 66 passed / 66 total
Cobertura: XX%
Commit: <hash>
```

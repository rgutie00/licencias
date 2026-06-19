# Task 4 Brief — Corregir importación relativa en engine_factory.py raíz

## Contexto
En `C:\desarrollos\licencias\` hay DOS archivos `engine_factory.py`:

1. `engine_factory.py` (raíz) — para uso standalone/scripts/CLI
2. `license_system/engine_factory.py` — para uso dentro del paquete Django

El archivo de la raíz tiene un bug: usa `from .license_engine import LicenseEngine` (importación relativa). Las importaciones relativas solo funcionan dentro de paquetes Python. Ejecutado desde la raíz lanza:
```
ImportError: attempted relative import with no known parent package
```

## Tu única tarea
Editar SOLO `engine_factory.py` en la RAÍZ (no `license_system/engine_factory.py`).

Cambiar la línea:
```python
from .license_engine import LicenseEngine
```

Por:
```python
from license_engine import LicenseEngine
```

**NO tocar** `license_system/engine_factory.py` — su importación relativa es correcta dentro del paquete Django.

## Verificación

Paso 1 — Confirmar que el import funciona desde raíz:
```
cd C:\desarrollos\licencias
python -c "import sys; sys.path.insert(0, '.'); from engine_factory import get_engine; print('import OK')"
```
Resultado esperado: falla con error de Django settings (no de importación). Aceptable cualquier output que NO contenga "ImportError" ni "attempted relative import".

Paso 2 — Confirmar que los tests siguen pasando:
```
python -m pytest test_license_engine.py -v --tb=short
```
Resultado esperado: 66 tests PASSED.

Paso 3 — Confirmar que `license_system/engine_factory.py` NO fue modificado:
```
python -c "
content = open('license_system/engine_factory.py').read()
assert 'from .license_engine' in content, 'ERROR: se modificó license_system/engine_factory.py'
print('license_system/engine_factory.py intacto')
"
```

## Commit
```
git add engine_factory.py
git commit -m "fix(fase1): corregir importacion relativa en engine_factory.py raiz"
```

## Reporte
Escribir en `.superpowers\sdd\task-4-report.md`:
```
Status: DONE
Fix: from .license_engine → from license_engine
Tests: 66 passed
Commit: <hash>
```

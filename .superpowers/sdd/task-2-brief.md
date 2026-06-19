# Task 2 Brief — test_last_check_malformado

## Contexto
Estás trabajando en `C:\desarrollos\licencias\`. Los tests de `test_license_engine.py` ahora tienen 59 tests (todos pasan). Queda una brecha de cobertura en las líneas 339-340 de `license_engine.py`: el handler `except ValueError` cuando `last_online_check` contiene un string no parseable como fecha ISO.

## Tu única tarea
Agregar UN SOLO método de test dentro de la clase `TestValidateOffline` existente en `test_license_engine.py`, después del método `test_license_type_trial` (el último método de esa clase).

## Código exacto a agregar

Dentro de `class TestValidateOffline:`, después de `test_license_type_trial`, agregar:

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

**IMPORTANTE:** Este método va DENTRO de la clase `TestValidateOffline` (con 4 espacios de indentación), NO al final del archivo.

## Verificación
```
cd C:\desarrollos\licencias
python -m pytest test_license_engine.py::TestValidateOffline::test_last_check_malformado_usa_fallback -v
```
Resultado esperado: 1 test PASSED.

Luego:
```
python -m pytest test_license_engine.py -v
```
Resultado esperado: 60 tests PASSED.

## Commit
```
git add test_license_engine.py
git commit -m "test(fase1): cubrir handler de last_online_check malformado"
```

## Reporte
Escribir resultado en `.superpowers\sdd\task-2-report.md`:
```
Status: DONE
Tests: 60 passed / 60 total
Commit: <hash>
```

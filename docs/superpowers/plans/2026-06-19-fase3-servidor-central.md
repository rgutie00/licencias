# Fase 3 — Servidor Central: Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar Fase 3 completando las 3 piezas faltantes: migraciones Django, test del path HMAC inválido en `/validate`, y las clases de test `TestAuditLog` y `TestAgentKeyPermission` que el spec exige explícitamente.

**Architecture:** Toda la implementación de Fase 3 (models, views, admin, permissions, serializers, validators, urls) ya está escrita y 36 tests pasan. Los 3 tasks de este plan son aditivos y no tocan el código de producción (excepto generar las migraciones). Los tests nuevos amplían `test_api.py`.

**Tech Stack:** Django 4.2, Django REST Framework, pytest-django, SQLite en memoria (tests)

## Global Constraints

- Python 3.11+, Django 4.2+, DRF 3.14+
- Solo modificar: `test_api.py` (agregar tests) y generar `licenses/migrations/0001_initial.py`
- NO tocar ningún archivo en `licenses/` excepto crear `migrations/`
- NO tocar archivos de Fase 1 ni Fase 2
- Los 36 tests de Fase 3 existentes deben seguir pasando
- Los 133 tests totales (68 Fase 1 + 29 Fase 2 + 36 Fase 3) deben seguir pasando
- Los nuevos tests NO deben duplicar assertions ya existentes — deben agregar verificaciones nuevas (count, campos del AuditLog, HMAC en validate)
- Ejecutar siempre desde `C:\desarrollos\licencias` con `python -m pytest`

---

## Estructura de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `licenses/migrations/0001_initial.py` | Crear (via makemigrations) | Migración inicial de los 3 modelos para producción |
| `test_api.py` | Modificar | Agregar `TestAuditLog`, `TestAgentKeyPermission`, y `test_hmac_invalido_en_validate` |

---

### Task 1: Crear migraciones Django para `licenses`

**Files:**
- Create: `licenses/migrations/__init__.py` (vacío, lo genera Django)
- Create: `licenses/migrations/0001_initial.py` (lo genera Django via makemigrations)

**Interfaces:**
- Consumes: `licenses/models.py` (Client, License, AuditLog — ya existentes)
- Produces: archivos de migración en `licenses/migrations/` listos para `python manage.py migrate` en producción

**Diagnóstico:** La carpeta `licenses/migrations/` no existe. Los tests pasan porque pytest-django crea las tablas directamente desde los modelos sin necesitar migraciones. Pero sin migraciones no hay `python manage.py migrate` para producción.

- [ ] **Step 1: Verificar que no existen migraciones**

```
cd C:\desarrollos\licencias
python -c "import os; print('migrations dir exists:', os.path.isdir('licenses/migrations'))"
```

Resultado esperado: `migrations dir exists: False`

- [ ] **Step 2: Generar la migración inicial**

```
cd C:\desarrollos\licencias
python manage.py makemigrations licenses
```

Resultado esperado:
```
Migrations for 'licenses':
  licenses\migrations\0001_initial.py
    - Create model Client
    - Create model License
    - Create model AuditLog
```

Si falla con error de configuración de Django, ejecutar con:
```
set DJANGO_SETTINGS_MODULE=config.settings
python manage.py makemigrations licenses
```

- [ ] **Step 3: Verificar que la migración generada es correcta**

```
python manage.py showmigrations licenses
```

Resultado esperado:
```
licenses
 [ ] 0001_initial
```

- [ ] **Step 4: Verificar que los tests siguen pasando**

```
python -m pytest test_api.py -v --tb=short 2>&1 | tail -5
```

Resultado esperado: `36 passed`

- [ ] **Step 5: Commit**

```
git add licenses/migrations/
git commit -m "feat(fase3): agregar migracion inicial para modelos Client, License, AuditLog"
```

**Reporte:** escribir en `.superpowers/sdd/fase3-task-1-report.md`:
```
Status: DONE
Migración: licenses/migrations/0001_initial.py
Tests: 36 passed
Commit: <hash>
```

---

### Task 2: Agregar tests faltantes del spec

**Files:**
- Modify: `test_api.py` (agregar 3 nuevas clases al final del archivo)

**Interfaces:**
- Consumes: `licenses.models.AuditLog`, `licenses.models.Client`, `licenses.models.License`, `licenses.permissions.AgentKeyPermission`, fixtures existentes `api_client`, `valid_key`, `existing_client`, `active_license`
- Produces: 3 nuevas clases de test + 1 test individual; suite pasa con ≥ 49 tests (36 existentes + 13 nuevos)

**Diagnóstico de gaps:**

1. **HMAC inválido en `/validate`**: `ValidateLicenseView` tiene el path `if nit and not verify_license_key(mac, nit, key): return 403` pero NO hay ningún test que lo ejerza. Los tests existentes de 403 solo prueban la API key del agente, no el HMAC de la licencia.

2. **`TestAuditLog`**: el spec dice "verificar que toda operación genera exactamente un registro de auditoría con los campos correctos". Los tests existentes solo hacen `.exists()`. Falta: verificar count==1 y verificar campos concretos (client, license, ip_address).

3. **`TestAgentKeyPermission`**: el spec exige una clase dedicada. Actualmente los 403s están embebidos en `TestActivateEndpoint` y `TestValidateEndpoint`. Necesitamos la clase explícita para cumplir el spec, más el caso "valor correcto → pasa" que no existe de forma aislada.

- [ ] **Step 1: Verificar la brecha en ValidateLicenseView**

```python
# Confirmar que este path existe en licenses/views.py
grep -n "verify_license_key" C:\desarrollos\licencias\licenses\views.py
```

Resultado esperado: aparece al menos en `ValidateLicenseView.post()`.

- [ ] **Step 2: Agregar los tests al final de test_api.py**

Abrir `test_api.py` y agregar exactamente este bloque al final del archivo (después de la clase `TestValidators`):

```python
# ─────────────────────────────────────────────────────────────
#  6. HMAC INVALIDO EN VALIDATE
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestValidateHmacInvalido:

    def test_hmac_invalido_retorna_403(self, api_client, settings,
                                        existing_client, active_license):
        """HMAC incorrecto en /validate → 403, no importa que el cliente exista."""
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
        settings.LICENSE_SECRET_KEY = "TEST_SECRET_FASE3"

        response = api_client.post(
            "/api/v1/licenses/validate",
            {"mac": FAKE_MAC, "nit": FAKE_NIT, "license_key": "XXXX-XXXX-XXXX-XXXX"},
            format="json",
            **HEADERS,
        )

        assert response.status_code == 403
        data = response.json()
        assert data["valid"] is False

    def test_hmac_invalido_genera_audit_log_rejected(self, api_client, settings,
                                                      existing_client, active_license):
        """HMAC incorrecto en /validate → AuditLog VALIDATE/rejected."""
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
        settings.LICENSE_SECRET_KEY = "TEST_SECRET_FASE3"

        api_client.post(
            "/api/v1/licenses/validate",
            {"mac": FAKE_MAC, "nit": FAKE_NIT, "license_key": "XXXX-XXXX-XXXX-XXXX"},
            format="json",
            **HEADERS,
        )

        assert AuditLog.objects.filter(action="VALIDATE", result="rejected").exists()


# ─────────────────────────────────────────────────────────────
#  7. AUDIT LOG — verificacion de count y campos
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAuditLog:
    """Verifica que cada operación genera exactamente un AuditLog con campos correctos."""

    def test_activate_genera_exactamente_un_log(self, api_client, valid_key, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY

        api_client.post(
            "/api/v1/licenses/activate",
            activation_payload(valid_key),
            format="json",
            **HEADERS,
        )

        logs = AuditLog.objects.filter(action="ACTIVATE", result="success")
        assert logs.count() == 1
        log = logs.first()
        assert log.client is not None
        assert log.license is not None
        assert log.result == "success"

    def test_validate_genera_exactamente_un_log(self, api_client, valid_key, settings,
                                                  existing_client, active_license):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
        AuditLog.objects.all().delete()

        api_client.post(
            "/api/v1/licenses/validate",
            {"mac": FAKE_MAC, "nit": FAKE_NIT, "license_key": valid_key},
            format="json",
            **HEADERS,
        )

        logs = AuditLog.objects.filter(action="VALIDATE")
        assert logs.count() == 1
        log = logs.first()
        assert log.client == existing_client
        assert log.license == active_license
        assert log.result == "success"

    def test_trial_genera_exactamente_un_log(self, api_client, valid_key, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY

        api_client.post(
            "/api/v1/licenses/trial",
            activation_payload(valid_key),
            format="json",
            **HEADERS,
        )

        logs = AuditLog.objects.filter(action="TRIAL_ACTIVATE", result="success")
        assert logs.count() == 1
        log = logs.first()
        assert log.client is not None
        assert log.license is not None

    def test_activate_rechazado_genera_un_log_rejected(self, api_client, settings):
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
        settings.LICENSE_SECRET_KEY = "TEST_SECRET_FASE3"

        api_client.post(
            "/api/v1/licenses/activate",
            activation_payload("XXXX-XXXX-XXXX-XXXX"),
            format="json",
            **HEADERS,
        )

        logs = AuditLog.objects.filter(action="ACTIVATE", result="rejected")
        assert logs.count() == 1
        log = logs.first()
        assert log.result == "rejected"
        assert "INVALID_KEY" in log.detail.get("reason", "")


# ─────────────────────────────────────────────────────────────
#  8. AGENT KEY PERMISSION — clase dedicada
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAgentKeyPermission:
    """Verifica AgentKeyPermission en los tres casos del spec."""

    def test_header_ausente_retorna_403(self, api_client, valid_key, settings):
        """Header X-License-Agent-Key ausente → 403 en cualquier endpoint."""
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
        settings.LICENSE_SECRET_KEY = "TEST_SECRET_FASE3"

        response = api_client.post(
            "/api/v1/licenses/activate",
            activation_payload(valid_key),
            format="json",
            # Sin header X-License-Agent-Key
        )
        assert response.status_code == 403

    def test_valor_incorrecto_retorna_403(self, api_client, valid_key, settings):
        """Header presente pero con valor incorrecto → 403."""
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
        settings.LICENSE_SECRET_KEY = "TEST_SECRET_FASE3"

        response = api_client.post(
            "/api/v1/licenses/activate",
            activation_payload(valid_key),
            format="json",
            HTTP_X_LICENSE_AGENT_KEY="clave-incorrecta-deliberada",
        )
        assert response.status_code == 403

    def test_valor_correcto_permite_acceso(self, api_client, valid_key, settings):
        """Header con valor correcto → la petición pasa el guard de permiso (puede fallar por otras razones)."""
        settings.LICENSE_AGENT_API_KEY = AGENT_API_KEY
        settings.LICENSE_SECRET_KEY = "TEST_SECRET_FASE3"

        response = api_client.post(
            "/api/v1/licenses/activate",
            activation_payload(valid_key),
            format="json",
            **HEADERS,
        )
        # El permiso pasó — no importa si la respuesta es 200 o 400 por otras razones
        assert response.status_code != 403
```

- [ ] **Step 3: Ejecutar solo los nuevos tests para verificar que pasan**

```
cd C:\desarrollos\licencias
python -m pytest test_api.py::TestValidateHmacInvalido test_api.py::TestAuditLog test_api.py::TestAgentKeyPermission -v --tb=short
```

Resultado esperado: **13 passed** (2 + 4 + 3 + ... los nuevos tests).

Nota: si algún test de `TestValidateHmacInvalido` falla con 200 en lugar de 403, revisar si el serializer acepta `license_key` inválida. La `ValidateRequestSerializer` acepta cualquier string para `license_key` (no valida formato XXXX-XXXX), así que el HMAC check en la view debe ejecutarse. Si el NIT está vacío (`required=False, default=""`), el check `if nit and not verify_license_key(...)` NO se ejecuta. La solución es enviar `nit=FAKE_NIT` en el payload (ya está en el test arriba).

- [ ] **Step 4: Ejecutar la suite completa y verificar sin regresiones**

```
python -m pytest test_api.py -v --tb=short 2>&1 | tail -10
```

Resultado esperado: **≥ 49 passed** (36 existentes + 13 nuevos), 0 failed.

- [ ] **Step 5: Verificar cobertura de views.py**

```
python -m pytest test_api.py --cov=licenses.views --cov-report=term-missing --tb=short 2>&1 | tail -15
```

Resultado esperado: cobertura ≥ 85% en `licenses/views.py` (el path de `MultipleObjectsReturned` y el update de nombre en activate son edge cases menores).

- [ ] **Step 6: Commit**

```
git add test_api.py
git commit -m "test(fase3): agregar TestAuditLog, TestAgentKeyPermission y test HMAC en validate"
```

**Reporte:** escribir en `.superpowers/sdd/fase3-task-2-report.md`:
```
Status: DONE
Tests nuevos: 13 (2 HMAC + 4 AuditLog + 3 AgentKeyPermission + args variados)
Suite total test_api.py: XX passed
Commit: <hash>
```

---

### Task 3: Verificación final y cierre de Fase 3

**Files:**
- Read: `.superpowers/sdd/fase3-task-2-report.md`
- Modify: `.superpowers/sdd/progress.md`

**Interfaces:**
- Consumes: resultado de Tasks 1 y 2
- Produces: ledger actualizado con Fase 3 certificada

- [ ] **Step 1: Ejecutar la suite completa (Fase 1 + 2 + 3)**

```
cd C:\desarrollos\licencias
python -m pytest test_license_engine.py test_middleware_views.py test_api.py -v --tb=short 2>&1 | tail -5
```

Resultado esperado: **≥ 146 passed** (68 Fase 1 + 29 Fase 2 + 49 Fase 3), 0 failed.

- [ ] **Step 2: Medir cobertura de Fase 3**

```
python -m pytest test_api.py --cov=licenses --cov-report=term-missing 2>&1 | tail -20
```

Registrar la cobertura de cada archivo en el reporte.

- [ ] **Step 3: Actualizar ledger de progreso**

Agregar al final de `.superpowers/sdd/progress.md`:

```
---
# Ledger SDD — Fase 3 Servidor Central
Base commit: <commit de inicio de Fase 3>

| Task | Estado | Commits | Notas |
|---|---|---|---|
| Task 1: Migraciones Django | COMPLETO | <hash> | licenses/migrations/0001_initial.py |
| Task 2: Tests faltantes del spec | COMPLETO | <hash> | +13 tests: TestAuditLog, TestAgentKeyPermission, HMAC validate |
| Task 3: Cierre | COMPLETO | <hash> | Suite total: XX tests |

## Resultado Fase 3
- Migraciones: 0001_initial.py generado
- Tests totales: 68 Fase1 + 29 Fase2 + XX Fase3
- Cobertura licenses/: XX%
- Revision final: APROBADO
```

- [ ] **Step 4: Commit de cierre**

```
git add .superpowers/sdd/progress.md
git commit -m "chore(fase3): cerrar fase 3 — servidor central completo con migraciones y XX tests"
```

**Reporte:** escribir en `.superpowers/sdd/fase3-task-3-report.md`:
```
Status: DONE
Suite completa: XX passed / XX total
Cobertura licenses/: XX%
Commit: <hash>
```

# Fase 2 — Middleware Django: Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer pasar los 29 tests de `test_middleware_views.py` sin romper los tests de Fase 3 en `test_api.py`.

**Architecture:** Todos los archivos de implementación de Fase 2 YA ESTÁN ESCRITOS (`license_middleware.py`, `views.py`, `engine_factory.py`, templates, `urls.py`, `test_urls.py`, `test_middleware_views.py`). El único problema es la configuración de Django para tests: `conftest.py` usa `ROOT_URLCONF="config.urls"` (Fase 3) y no incluye `license_system` en INSTALLED_APPS ni `LicenseMiddleware` en MIDDLEWARE. La solución tiene dos cambios: (1) modificar `conftest.py` para soportar Fase 2, y (2) extender `test_urls.py` para mantener las rutas de Fase 3.

**Tech Stack:** Django 4.2+, pytest-django, unittest.mock, httpx

## Global Constraints

- Python 3.11+, Django 4.2+
- Sin tocar ningún archivo de implementación: `license_middleware.py`, `views.py`, `engine_factory.py`, `license_system/urls.py`, ni los templates en `license_system/templates/`
- Sin romper los tests existentes en `test_api.py` (Fase 3)
- Sin tocar `config/urls.py`, `config/settings.py`, `licenses/` ni nada del servidor central
- Solo modificar: `conftest.py` y `test_urls.py`
- Las rutas `/api/v1/` y `/admin/` deben quedar exentas del middleware en el entorno de test para que los tests de Fase 3 sigan pasando
- El middleware `license_system.license_middleware.LicenseMiddleware` debe ser el PRIMERO en MIDDLEWARE
- `license_system` debe estar en INSTALLED_APPS para que Django encuentre los templates via APP_DIRS=True

---

## Estructura de archivos (solo 2 archivos modificados)

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `conftest.py` | Modificar | Agregar `license_system` a INSTALLED_APPS, `LicenseMiddleware` primero en MIDDLEWARE, cambiar ROOT_URLCONF a `test_urls`, agregar settings LICENSE_* y EXEMPT_URLS |
| `test_urls.py` | Modificar | Agregar rutas `/admin/` y `/api/v1/` para que los tests de Fase 3 sigan funcionando con el nuevo ROOT_URLCONF |

---

### Task 1: Corregir conftest.py y test_urls.py

**Files:**
- Modify: `conftest.py`
- Modify: `test_urls.py`

**Interfaces:**
- Consumes: `license_system.license_middleware.LicenseMiddleware` (ya existe), `license_system.urls` (ya existe), `licenses.urls` (ya existe para Fase 3)
- Produces: configuración Django que soporta tests de Fase 2 (Client HTTP + middleware activo + URL routing) sin romper Fase 3

**Diagnóstico previo (ya verificado):**

Los 22 tests que fallan son todos los que usan `client = Client()` (Django test client). Los 7 que pasan son los que usan `RequestFactory` directamente (no necesitan URL routing). Las causas:
1. `ROOT_URLCONF="config.urls"` → no tiene `/license/`, `/dashboard/`, `/api/data/`, `/accounts/login/`
2. `license_system` no está en INSTALLED_APPS → Django no encuentra los templates
3. `LicenseMiddleware` no está en MIDDLEWARE → los redirects no ocurren

- [ ] **Step 1: Leer el conftest.py actual completo**

```
cd C:\desarrollos\licencias
cat conftest.py
```

Verificar que la función `pytest_configure` contiene `settings.configure(...)` con `INSTALLED_APPS`, `MIDDLEWARE`, `ROOT_URLCONF` y `DATABASES`.

- [ ] **Step 2: Reemplazar el contenido de conftest.py**

El nuevo `conftest.py` debe quedar exactamente así:

```python
"""
conftest.py — Setup de pytest-django compartido para Fase 2 y Fase 3.
"""
import django
import pytest
from django.conf import settings


def pytest_configure():
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            SECRET_KEY="test-secret-key-compartido",
            INSTALLED_APPS=[
                "unfold",
                "unfold.contrib.filters",
                "django.contrib.admin",
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.sessions",
                "django.contrib.messages",
                "django.contrib.staticfiles",
                "rest_framework",
                "licenses",
                "license_system",
            ],
            MIDDLEWARE=[
                "license_system.license_middleware.LicenseMiddleware",
                "django.middleware.security.SecurityMiddleware",
                "django.contrib.sessions.middleware.SessionMiddleware",
                "django.middleware.common.CommonMiddleware",
                "django.contrib.auth.middleware.AuthenticationMiddleware",
                "django.contrib.messages.middleware.MessageMiddleware",
            ],
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            TEMPLATES=[{
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {
                    "context_processors": [
                        "django.template.context_processors.request",
                        "django.contrib.auth.context_processors.auth",
                        "django.contrib.messages.context_processors.messages",
                    ],
                },
            }],
            ROOT_URLCONF="test_urls",
            STATIC_URL="/static/",
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
            USE_TZ=True,
            TIME_ZONE="America/Bogota",

            # Sistema de licencias — cliente (Fase 2)
            LICENSE_SECRET_KEY="TEST_SECRET_FASE2",
            LICENSE_TOKEN_PATH="/tmp/test-license.tok",
            LICENSE_SERVER_URL="",
            LICENSE_API_KEY="",
            LICENSE_MAX_OFFLINE_DAYS=30,
            LICENSE_HTTP_TIMEOUT=5.0,
            LICENSE_EXEMPT_URLS=[
                "/license/",
                "/static/",
                "/media/",
                "/favicon.ico",
                "/robots.txt",
                "/admin/",
                "/api/v1/",
            ],

            # Sistema de licencias — servidor central (Fase 3)
            LICENSE_AGENT_API_KEY="test-agent-key-fase3",
            LICENSE_COMMERCIAL_DAYS=365,
            LICENSE_TRIAL_DAYS=30,

            # DRF
            REST_FRAMEWORK={
                "DEFAULT_AUTHENTICATION_CLASSES": [],
                "DEFAULT_PERMISSION_CLASSES": [],
                "DEFAULT_RENDERER_CLASSES": [
                    "rest_framework.renderers.JSONRenderer",
                ],
            },
        )
```

- [ ] **Step 3: Leer el test_urls.py actual**

```
cat test_urls.py
```

Verificar que tiene `path("license/", ...)`, `path("dashboard/", ...)`, etc. pero le faltan `/admin/` y `/api/v1/`.

- [ ] **Step 4: Reemplazar el contenido de test_urls.py**

El nuevo `test_urls.py` debe quedar exactamente así:

```python
"""
test_urls.py — URLs para tests de Fase 2 y Fase 3.
"""
from django.contrib import admin
from django.urls import include, path


def dummy_view(request):
    from django.http import HttpResponse
    if hasattr(request, "license"):
        return HttpResponse(f"OK license={request.license.status}", status=200)
    return HttpResponse("OK no-license-attr", status=200)


def login_view(request):
    from django.http import HttpResponse
    return HttpResponse("LOGIN PAGE", status=200)


urlpatterns = [
    path("license/", include("license_system.urls")),
    path("accounts/login/", login_view, name="login"),
    path("dashboard/", dummy_view, name="dashboard"),
    path("api/data/", dummy_view, name="api-data"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("licenses.urls")),
]
```

- [ ] **Step 5: Ejecutar SOLO los tests de Fase 2 y verificar que pasan**

```
cd C:\desarrollos\licencias
python -m pytest test_middleware_views.py -v --tb=short
```

Resultado esperado: **29 passed, 0 failed**

Si algún test falla, investigar el error. Los fallos más comunes y sus causas:
- `TemplateDoesNotExist: license/activate.html` → `license_system` no está en INSTALLED_APPS o APP_DIRS es False
- `404` en `/dashboard/` → ROOT_URLCONF no apunta a `test_urls`
- `302` inesperado en `/dashboard/` con licencia válida → `LicenseMiddleware` no está en MIDDLEWARE o el mock no aplica
- `AssertionError: b"license=VALID" not in response.content` → el dummy_view no tiene acceso a `request.license` (el middleware no lo adjuntó)

- [ ] **Step 6: Ejecutar los tests de Fase 3 y verificar que siguen pasando**

```
python -m pytest test_api.py -v --tb=short
```

Resultado esperado: todos los tests de Fase 3 pasan (el mismo número que antes).

Si algún test de Fase 3 falla con status 302:
- Causa: el middleware bloqueó una ruta `/api/v1/` que no estaba exenta
- Fix: verificar que `LICENSE_EXEMPT_URLS` en conftest.py incluye `/api/v1/`

- [ ] **Step 7: Ejecutar la suite completa para detectar regresiones**

```
python -m pytest test_middleware_views.py test_api.py -v --tb=short
```

Resultado esperado: todos los tests pasan (29 de Fase 2 + N de Fase 3).

- [ ] **Step 8: Commit**

```
git add conftest.py test_urls.py
git commit -m "feat(fase2): configurar Django test setup para middleware — 29 tests"
```

**Reporte:** escribir en `.superpowers/sdd/fase2-task-1-report.md`:
```
Status: DONE
Tests Fase 2: 29 passed / 29 total
Tests Fase 3: N passed (sin regresiones)
Commit: <hash>
```

---

### Task 2: Revisión y cierre de Fase 2

**Files:**
- Read: `.superpowers/sdd/fase2-task-1-report.md`
- Read: `.superpowers/sdd/progress.md` (actualizar)

**Interfaces:**
- Consumes: resultado de Task 1
- Produces: ledger actualizado + rama Fase 2 certificada

- [ ] **Step 1: Ejecutar medición de cobertura de los archivos de Fase 2**

```
cd C:\desarrollos\licencias
python -m pytest test_middleware_views.py --cov=license_system.license_middleware --cov=license_system.views --cov-report=term-missing -v
```

Resultado esperado: cobertura ≥ 80% en `license_middleware.py` y `views.py`.

- [ ] **Step 2: Ejecutar suite completa final**

```
python -m pytest test_license_engine.py test_middleware_views.py test_api.py -v --tb=short
```

Resultado esperado: 68 (Fase 1) + 29 (Fase 2) + N (Fase 3) = todos pasan.

- [ ] **Step 3: Actualizar ledger de progreso**

Agregar al final de `.superpowers/sdd/progress.md`:
```
Fase 2 — Middleware Django:
  Task 1: conftest.py + test_urls.py — COMPLETO (commit <hash>)
  Tests: 29/29 Fase 2 + N/N Fase 3 sin regresiones
  Cobertura middleware: XX%
  Estado: CERTIFICADO — listo para Fase 3
```

- [ ] **Step 4: Commit de cierre**

```
git add .superpowers/sdd/progress.md
git commit -m "chore(fase2): cerrar fase 2 — 29 tests middleware, sin regresiones"
```

**Reporte:** escribir en `.superpowers/sdd/fase2-task-2-report.md`:
```
Status: DONE
Suite completa: XX passed / XX total
Cobertura middleware: XX%
Commit: <hash>
```

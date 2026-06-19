# Fase 2 — Middleware Django

**Archivos principales:** `license_middleware.py`, `engine_factory.py`, `license_system/views.py`  
**Dependencias:** Django 4.2+, motor criptográfico (Fase 1)  
**Punto de integración:** configuración `MIDDLEWARE` en `settings.py`

---

## 1. Propósito

El middleware de licencias intercepta todas las solicitudes HTTP entrantes antes de que lleguen a cualquier vista de la aplicación. Si la licencia no es válida, el usuario es redirigido automáticamente — sin que las vistas de negocio necesiten ningún cambio.

Esta arquitectura garantiza que el control de licencias sea:
- **Transparente** para las vistas existentes: no hay decoradores ni verificaciones manuales
- **Imposible de saltarse**: al estar en el middleware, no existe ruta de acceso que lo evite
- **Centralizado**: un solo punto de configuración y lógica

---

## 2. Posición en el Stack de Middleware

El middleware de licencias **debe ser el primero** en la lista `MIDDLEWARE` de `settings.py`:

```python
MIDDLEWARE = [
    "license_middleware.LicenseMiddleware",  # ← PRIMERO, sin excepción
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    ...
]
```

**Por qué debe ser el primero:** si la licencia es inválida, ningún usuario debería poder operar en la aplicación, independientemente de si está autenticado o no. Colocarlo después de `AuthenticationMiddleware` permitiría que las solicitudes lleguen a partes del framework antes de ser bloqueadas.

---

## 3. Rutas Exentas

Las siguientes rutas nunca son interceptadas por el middleware:

| Ruta | Razón |
|---|---|
| `/license/` | Evita redirección infinita: las vistas de activación deben ser accesibles cuando la licencia no es válida |
| `/static/` | Archivos estáticos (CSS, JS, imágenes) necesarios para renderizar las páginas de licencia |
| `/media/` | Archivos de medios — no deben bloquearse por estado de licencia |
| `/favicon.ico` | Solicitud automática del navegador; no representa uso de la aplicación |
| `/robots.txt` | Archivo de indexación web; no representa uso de la aplicación |

Si se agregan nuevas rutas de licencia (por ejemplo, `/license/api/`), deben añadirse explícitamente a la lista de exenciones en `_is_exempt()`.

---

## 4. Flujo de Decisión

```
Solicitud HTTP entrante
│
├─ ¿La ruta está exenta? ──SÍ──► Pasa directamente al siguiente middleware
│
└─ NO
   │
   ├─ engine.validate()
   │
   ├─ NO_LICENSE
   │    └─► redirect("/license/activate/")
   │
   ├─ TAMPERED
   │    └─► engine.delete_token() → redirect("/license/activate/?reason=tampered")
   │
   ├─ EXPIRED
   │    └─► redirect("/license/expired/")
   │
   ├─ CLOCK_ROLLBACK
   │    └─► engine.delete_token() → redirect("/license/activate/?reason=clock")
   │
   └─ VALID
        ├─ request.license = result
        ├─ ¿days_remaining ≤ 7?
        │    └─► request.license_warning = "⚠ Tu licencia vence en N día(s)..."
        └─► Siguiente middleware → Vista
```

**Nota sobre TAMPERED y CLOCK_ROLLBACK:** en ambos casos el token es borrado del disco antes de redirigir. Esto obliga al usuario a contactar al administrador para una nueva activación — no puede simplemente "reintentar" porque el token corrupto ya no existe.

---

## 5. Aviso de Vencimiento Próximo

Cuando la licencia es válida pero faltan 7 días o menos para el vencimiento, el middleware agrega al objeto `request`:

```python
request.license_warning = "⚠ Tu licencia vence en 3 día(s). Contacta a tu administrador."
```

**Cómo mostrarlo en plantillas:**

```html
{% if request.license_warning %}
<div class="alert alert-warning">
    {{ request.license_warning }}
</div>
{% endif %}
```

Esta lógica vive en el middleware para que aplique automáticamente a todas las páginas sin necesidad de modificar cada plantilla individualmente. Solo es necesario agregar el bloque de alerta en el template base (`base.html`).

---

## 6. Singleton del Engine (`engine_factory.py`)

El motor criptográfico es computacionalmente costoso de inicializar (PBKDF2 con 480.000 iteraciones en la primera derivación de clave). Por este motivo, `engine_factory.py` mantiene una única instancia del motor por proceso Django:

```python
_engine: LicenseEngine | None = None

def get_engine() -> LicenseEngine:
    global _engine
    if _engine is None:
        _engine = LicenseEngine(
            secret_key=settings.LICENSE_SECRET_KEY,
            token_path=Path(settings.LICENSE_TOKEN_PATH),
            server_url=settings.LICENSE_SERVER_URL,
            api_key=settings.LICENSE_API_KEY,
            max_offline_days=settings.LICENSE_MAX_OFFLINE_DAYS,
            http_timeout=settings.LICENSE_HTTP_TIMEOUT,
        )
    return _engine

def reset_engine():
    """Reinicia el singleton. Usar solo en tests."""
    global _engine
    _engine = None
```

`reset_engine()` se usa exclusivamente en los tests para garantizar un estado limpio entre casos de prueba.

---

## 7. Configuración en `settings.py`

Agregar el bloque completo en `settings.py` del proyecto Django cliente:

```python
# ── Licencias ────────────────────────────────────────────
LICENSE_SECRET_KEY    = env("LICENSE_SECRET_KEY")         # secreto compartido, mínimo 32 chars
LICENSE_TOKEN_PATH    = env("LICENSE_TOKEN_PATH",         # ruta absoluta del token en disco
                            default="/var/license/token.lic")
LICENSE_SERVER_URL    = env("LICENSE_SERVER_URL")         # URL del servidor central, sin /
LICENSE_API_KEY       = env("LICENSE_API_KEY")            # X-License-Agent-Key
LICENSE_MAX_OFFLINE_DAYS = int(env("LICENSE_MAX_OFFLINE_DAYS", default="30"))
LICENSE_HTTP_TIMEOUT  = float(env("LICENSE_HTTP_TIMEOUT", default="5.0"))
```

Y agregar `LicenseMiddleware` como primer elemento de `MIDDLEWARE` (ver sección 2).

### Variables de entorno requeridas

| Variable | Ejemplo | Descripción |
|---|---|---|
| `LICENSE_SECRET_KEY` | `s3cr3t-32-chars-minimum-random!!` | Idéntico al configurado en el servidor central |
| `LICENSE_TOKEN_PATH` | `/var/license/token.lic` | El motor escribe y lee el token aquí |
| `LICENSE_SERVER_URL` | `https://licencias.miempresa.com` | Sin barra final |
| `LICENSE_API_KEY` | `ag3nt-k3y-s3cur0` | Idéntico al configurado en el servidor central |
| `LICENSE_MAX_OFFLINE_DAYS` | `30` | Días máximos sin conexión (default: 30) |
| `LICENSE_HTTP_TIMEOUT` | `5.0` | Timeout HTTP en segundos (default: 5.0) |

---

## 8. Vistas de Licencia (`license_system/views.py`)

### `activate(request)` — Formulario de activación

- **GET:** Renderiza el formulario con campos NIT y nombre de empresa
- **POST:** Genera la clave de licencia localmente (`engine.generate_key(mac, nit)`) y la envía al servidor central junto con NIT y nombre

**Respuestas del servidor central:**

| HTTP | Significado | Acción |
|---|---|---|
| `200 OK` | Activación exitosa | Llama a `engine.activate_from_response()`, redirige a `/license/success/` |
| `409 Conflict` | Prueba gratuita ya utilizada | Muestra mensaje de error en el formulario |
| `403 Forbidden` | Clave inválida o empresa no autorizada | Muestra mensaje de rechazo |
| Error de red | Servidor central inaccesible | Muestra mensaje de error de conectividad |

**Flujo de datos en la activación:**

```
Usuario ingresa NIT
        │
        ▼
Cliente genera clave localmente:
generate_key(mac_local, nit)  →  "XXXX-XXXX-XXXX-XXXX"
        │
        ▼
POST al servidor central:
{ mac, nit, license_key, company_name }
        │
        ▼
Servidor verifica HMAC y crea licencia
        │
        ▼
Respuesta: { expiry_date, license_type, server_time }
        │
        ▼
activate_from_response() → cifra token → guarda en disco
```

### `expired(request)` — Página de licencia vencida

Renderiza una página informativa que indica que la licencia ha expirado e instruye al usuario para contactar al administrador.

### `success(request)` — Confirmación de activación

Renderiza una página de confirmación post-activación con los detalles básicos de la nueva licencia.

---

## 9. Pruebas

La suite usa `django.test.TestClient` para simular solicitudes HTTP sin servidor real:

| Caso de prueba | Qué verifica |
|---|---|
| Rutas exentas (5 rutas) | Pasan sin invocar `validate()` |
| Estado `NO_LICENSE` | Redirige a `/license/activate/` |
| Estado `TAMPERED` | Borra token + redirige con `?reason=tampered` |
| Estado `EXPIRED` | Redirige a `/license/expired/` |
| Estado `CLOCK_ROLLBACK` | Borra token + redirige con `?reason=clock` |
| Estado `VALID` | `request.license` disponible en la vista |
| Aviso de 7 días | `request.license_warning` presente |
| Sin aviso con 8+ días | `request.license_warning` ausente |

El engine se mockea en todos los tests de middleware para aislar la lógica de redirección de la criptografía real.

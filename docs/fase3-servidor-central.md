# Fase 3 — Servidor Central

**Archivos principales:** `licenses/models.py`, `licenses/views.py`, `licenses/admin.py`  
**Framework:** Django 4.2 + Django REST Framework  
**Base de datos:** PostgreSQL 14+  
**Panel de administración:** django-unfold

---

## 1. Propósito

El servidor central es la fuente de verdad del sistema de licencias. Centraliza:
- La autorización de nuevas activaciones (comerciales y de prueba)
- La validación periódica de licencias activas
- El registro inmutable de todas las operaciones
- La gestión operativa desde el panel de administración

Los motores cliente se comunican con el servidor central en cada validación online. Si el servidor no responde, el motor cae a modo offline (ver Fase 1). Si la licencia es revocada desde el servidor, el cliente lo descubre en la próxima validación online exitosa.

---

## 2. Arquitectura

```
Motor cliente (Fase 1)
        │
        │ HTTPS  POST /licenses/activate/
        │        POST /licenses/validate/
        │        POST /licenses/trial/
        ▼
┌───────────────────────────────────────┐
│           Django + DRF                │
│                                       │
│  AgentKeyPermission                   │
│  (verifica X-License-Agent-Key)       │
│           │                           │
│           ▼                           │
│  ActivateLicenseView                  │
│  ValidateLicenseView                  │
│  TrialLicenseView                     │
│           │                           │
│           ▼                           │
│  ┌────────────────────────────────┐   │
│  │ PostgreSQL                     │   │
│  │  ├─ Client (mac + nit únicos)  │   │
│  │  ├─ License (estados)          │   │
│  │  └─ AuditLog (solo append)     │   │
│  └────────────────────────────────┘   │
│                                       │
│  Panel Admin (django-unfold)          │
│  ClientAdmin / LicenseAdmin /         │
│  AuditLogAdmin                        │
└───────────────────────────────────────┘
```

---

## 3. Modelos de Datos

### `Client` — Empresa cliente

Identifica de forma única a cada empresa por la combinación `(mac, nit)`. Una vez registrado, estos campos son inmutables.

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | Clave primaria, generada automáticamente |
| `mac` | CharField(12) | MAC normalizada (sin separadores, uppercase). Ej: `AABBCCDDEEFF` |
| `nit` | CharField(20) | NIT normalizado uppercase. Ej: `900123456-7` |
| `name` | CharField(200) | Nombre de la empresa |
| `trial_used` | BooleanField | `True` si ya usó la prueba gratuita. Solo SuperAdmin puede resetear. |
| `anomalies_count` | PositiveIntegerField | Contador de rollbacks de reloj y tokens manipulados detectados |
| `created_at` | DateTimeField | Fecha de registro (auto) |
| `updated_at` | DateTimeField | Última modificación (auto) |

**Restricciones:**
- `unique_together = [("mac", "nit")]` — dos servidores con distinta MAC son clientes distintos aunque tengan el mismo NIT
- Índices en `(mac, nit)` y `(nit)` para búsquedas rápidas en validación

**Property `active_license`:** devuelve la licencia con `status="active"` y `expiry_date > now()`, o `None` si no existe.

---

### `License` — Licencia de software

Registra cada licencia emitida. Un cliente puede tener múltiples licencias históricas, pero solo una activa vigente a la vez (enforced en la lógica de activación, no con restricción de BD).

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | Clave primaria |
| `client` | FK → Client | Empresa a la que pertenece |
| `license_type` | CharField | `"commercial"` o `"trial"` |
| `status` | CharField | `"active"`, `"expired"`, `"revoked"`, `"pending"` |
| `expiry_date` | DateTimeField | Fecha y hora de vencimiento (UTC) |
| `activated_at` | DateTimeField | Cuándo fue activada (auto) |
| `activated_by` | FK → User (nullable) | Admin que la activó manualmente (null si fue via API) |
| `last_validated_at` | DateTimeField (nullable) | Última validación online recibida |
| `revoked_at` | DateTimeField (nullable) | Cuándo fue revocada |
| `revoked_by` | FK → User (nullable) | Admin que la revocó |
| `notes` | TextField | Observaciones del administrador |

**Properties:**
- `is_valid`: `status == "active" AND expiry_date > now()`
- `days_remaining`: días hasta el vencimiento (0 si no es válida)

**Método `revoke(user, note)`:** cambia status a `"revoked"`, guarda `revoked_at` y `revoked_by`, agrega nota. Debe llamarse siempre a través de este método para garantizar integridad.

---

### `AuditLog` — Registro inmutable

Registra todas las operaciones del sistema. **Nunca se edita ni se elimina** — es el historial definitivo de lo que ocurrió.

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | BigAutoField | Entero autoincremental (optimizado para inserciones frecuentes) |
| `action` | CharField | Tipo de acción (ver tabla de acciones) |
| `license` | FK → License (nullable) | Licencia afectada |
| `client` | FK → Client (nullable) | Cliente afectado |
| `ip_address` | GenericIPAddressField | IP del solicitante |
| `result` | CharField | `"success"`, `"rejected"`, `"error"` |
| `detail` | JSONField | Datos adicionales libres (razón de rechazo, admin que actuó, etc.) |
| `admin_user` | FK → User (nullable) | Usuario admin si la acción fue desde el panel |
| `created_at` | DateTimeField | Timestamp de la operación (auto, indexado) |

**Tipos de acción:**

| Acción | Cuándo se genera | Color en admin |
|---|---|---|
| `ACTIVATE` | Activación comercial exitosa o extensión de días | Verde |
| `VALIDATE` | Validación online (exitosa o rechazada) | Cian |
| `TRIAL_ACTIVATE` | Activación de prueba | Violeta |
| `REVOKE` | Revocación desde el panel | Rojo |
| `ANOMALY` | Rollback de reloj o token manipulado reportado | Amarillo |
| `MANUAL_ACTIVATE` | Activación manual desde el admin | Verde |
| `TRIAL_RESET` | Reset de prueba gratuita por SuperAdmin | Amarillo |

**Helper `AuditLog.log()`:** método de clase para crear un registro en una línea desde cualquier parte del código:

```python
AuditLog.log(
    action="REVOKE",
    result="success",
    license=lic,
    client=lic.client,
    user=request.user,
    detail={"revoked_by": request.user.username},
)
```

---

## 4. API REST

### Autenticación

Todos los endpoints requieren el header:

```
X-License-Agent-Key: <valor configurado en LICENSE_API_KEY>
```

Implementado en `AgentKeyPermission`. Devuelve `HTTP 403` si el header está ausente o el valor no coincide.

Adicionalmente, cada operación verifica el HMAC de la clave de licencia para confirmar que el motor cliente es legítimo.

---

### `POST /licenses/activate/` — Activación comercial

**Request:**
```json
{
    "mac": "AABBCCDDEEFF",
    "nit": "900123456-7",
    "license_key": "XXXX-XXXX-XXXX-XXXX",
    "company_name": "Empresa S.A.S."
}
```

**Proceso:**
1. Verifica `X-License-Agent-Key`
2. Recalcula `HMAC(secret, mac + nit + VERSION_SALT)` y compara con `license_key`
3. `get_or_create(Client, mac=mac, nit=nit)` — registra la empresa si es nueva
4. Revoca todas las licencias activas anteriores del cliente
5. Crea nueva `License` con `expiry_date = now() + 365 días`, `license_type="commercial"`
6. Registra en `AuditLog`

**Respuestas:**

| HTTP | Cuerpo | Significado |
|---|---|---|
| `200 OK` | `{"expiry_date": "...", "license_type": "commercial", "server_time": "..."}` | Activación exitosa |
| `403 Forbidden` | `{"detail": "Clave de licencia inválida"}` | HMAC no coincide |
| `500` | `{"detail": "..."}` | Error interno del servidor |

---

### `POST /licenses/validate/` — Validación periódica

**Request:**
```json
{
    "mac": "AABBCCDDEEFF",
    "nit": "900123456-7",
    "license_key": "XXXX-XXXX-XXXX-XXXX"
}
```

**Proceso:**
1. Verifica `X-License-Agent-Key`
2. Verifica HMAC de la clave
3. Busca `Client` por `(mac, nit)` → `404` si no existe
4. Busca `License` activa del cliente
5. Si existe y es válida: actualiza `last_validated_at = now()`, registra `VALIDATE/success`
6. Si no existe o está revocada/vencida: registra `VALIDATE/rejected`

**Respuestas:**

| HTTP | Cuerpo | Significado |
|---|---|---|
| `200 OK` | `{"valid": true, "expiry_date": "...", "server_time": "..."}` | Licencia válida |
| `200 OK` | `{"valid": false, "reason": "revoked"}` | Licencia revocada |
| `200 OK` | `{"valid": false, "reason": "expired"}` | Licencia vencida |
| `403 Forbidden` | `{"detail": "Clave inválida"}` | HMAC no coincide |
| `404 Not Found` | `{"detail": "Cliente no encontrado"}` | MAC+NIT no registrados |

---

### `POST /licenses/trial/` — Prueba gratuita

**Request:**
```json
{
    "mac": "AABBCCDDEEFF",
    "nit": "900123456-7",
    "license_key": "XXXX-XXXX-XXXX-XXXX",
    "company_name": "Empresa S.A.S."
}
```

**Proceso:**
1. Verifica `X-License-Agent-Key` y HMAC
2. `get_or_create(Client, mac, nit)`
3. Si `client.trial_used == True` → `HTTP 409` (ya usó la prueba)
4. Crea `License` con `expiry_date = now() + 30 días`, `license_type="trial"`
5. Marca `client.trial_used = True` (permanente hasta reset por SuperAdmin)
6. Registra en `AuditLog`

**Respuestas:**

| HTTP | Cuerpo | Significado |
|---|---|---|
| `200 OK` | `{"expiry_date": "...", "license_type": "trial", "server_time": "..."}` | Prueba activada |
| `409 Conflict` | `{"detail": "La prueba gratuita ya fue utilizada"}` | Ya usó la prueba |
| `403 Forbidden` | `{"detail": "Clave inválida"}` | HMAC no coincide |

---

## 5. Panel de Administración

### `ClientAdmin` — Gestión de empresas

**Vista de lista** muestra para cada cliente:
- Nombre y NIT
- MAC (primeros 6 caracteres para no exponer la dirección completa)
- Estado de licencia activa con badge de color (verde/amarillo/rojo según días restantes)
- Estado de prueba gratuita (Disponible / Usada)
- Contador de anomalías

**Campos de solo lectura:** `id`, `mac`, `nit`, `trial_used`, `created_at`, `updated_at` — los identificadores del hardware y el estado de prueba no son editables desde el panel.

**Inline de licencias:** el detalle del cliente muestra el historial completo de licencias como tabla embebida (solo lectura, con enlace al detalle de cada licencia).

**Acción disponible:**

| Acción | Quién puede ejecutarla | Qué hace |
|---|---|---|
| Resetear prueba gratuita | Solo SuperAdmin | Pone `trial_used = False`, registra en AuditLog |

---

### `LicenseAdmin` — Gestión de licencias

**Vista de lista** muestra para cada licencia:
- Cliente, tipo de licencia, estado con badge de color
- Fecha de vencimiento y días restantes
- Última validación online

**Acciones disponibles:**

| Acción | Efecto | Propagación al cliente |
|---|---|---|
| **Revocar licencias** | Cambia `status = "revoked"`, guarda fecha y quién revocó | En la próxima `validate_online()` exitosa, el cliente recibe `valid: false` y el middleware redirige a `/license/expired/` |
| **Extender 30 días** | Suma 30 días a `expiry_date` | En la próxima `validate_online()` exitosa, el token local se actualiza con la nueva fecha |

**Nota:** la acción "Activar nueva licencia comercial" está declarada pero pendiente de implementación. La activación manual debe realizarse actualmente a través del endpoint de la API o contactando a soporte técnico.

---

### `AuditLogAdmin` — Solo lectura

El `AuditLog` no puede ser creado, editado ni eliminado desde el panel bajo ningún rol, incluyendo SuperAdmin. Los tres métodos de permiso de Django están sobreescritos para devolver `False` incondicionalmente:

```python
has_add_permission()    → False
has_change_permission() → False
has_delete_permission() → False
```

La vista de lista incluye un filtro por fecha (`date_hierarchy`) para navegar el historial por año/mes/día, y permite buscar por nombre de empresa, NIT o dirección IP.

---

## 6. Seguridad del Servidor

| Capa | Mecanismo |
|---|---|
| **Transporte** | HTTPS obligatorio — el motor cliente no hace peticiones HTTP planas |
| **Autenticación de agente** | `X-License-Agent-Key` verifica que quien llama es un motor cliente autorizado |
| **Verificación de identidad** | HMAC recalculado en el servidor valida que la clave corresponde a `(mac, nit)` con el secreto correcto |
| **Trazabilidad** | Toda operación queda en `AuditLog` con IP, timestamp y resultado |
| **Rotación de AgentKey** | Cambiar `LICENSE_API_KEY` en el servidor invalida motores cliente no actualizados sin modificar código |

---

## 7. Despliegue

### Variables de entorno requeridas en el servidor central

| Variable | Ejemplo | Descripción |
|---|---|---|
| `SECRET_KEY` | `django-insecure-...` | Secret key de Django |
| `DATABASE_URL` | `postgres://user:pass@host:5432/licencias` | Conexión a PostgreSQL |
| `LICENSE_SECRET_KEY` | `s3cr3t-32-chars-minimum-random!!` | Mismo valor que en los clientes |
| `LICENSE_API_KEY` | `ag3nt-k3y-s3cur0` | Valor del header X-License-Agent-Key |
| `ALLOWED_HOSTS` | `licencias.miempresa.com` | Hosts permitidos por Django |

### Pasos de instalación

```bash
# 1. Migraciones
python manage.py migrate

# 2. Crear superusuario para el panel admin
python manage.py createsuperuser

# 3. Recolectar estáticos
python manage.py collectstatic --noinput

# 4. Levantar el servidor (ejemplo con gunicorn)
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

---

## 8. Pruebas

La suite usa `APIClient` de DRF y fixtures de base de datos en memoria (SQLite para tests):

| Grupo | Casos cubiertos |
|---|---|
| `TestActivateLicense` | Activación exitosa, clave HMAC inválida, revocación de licencia anterior, cliente nuevo vs existente |
| `TestValidateLicense` | Licencia activa, licencia revocada, licencia vencida, cliente no registrado, HMAC inválido |
| `TestTrialLicense` | Primera prueba (éxito), segunda prueba (409 Conflict), HMAC inválido |
| `TestAuditLog` | Verificar que toda operación genera exactamente un registro de auditoría con los campos correctos |
| `TestAgentKeyPermission` | Header ausente → 403, valor incorrecto → 403, valor correcto → pasa |

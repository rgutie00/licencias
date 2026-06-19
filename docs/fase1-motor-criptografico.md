# Fase 1 — Motor Criptográfico

**Archivo principal:** `license_engine.py`  
**Dependencias:** `cryptography`, `psutil`, `httpx`, `hmac`, `hashlib`  
**Acoplamiento con Django:** ninguno — el motor es Python puro

---

## 1. Propósito

El motor criptográfico es el núcleo del sistema. Implementa todas las operaciones de seguridad de forma independiente de Django: puede ejecutarse en cualquier script Python que proporcione los parámetros de configuración. Esta independencia permite testearlo de forma aislada sin necesidad de levantar un proyecto Django.

Sus responsabilidades son:
- Identificar el servidor por la MAC de su NIC activa
- Generar y verificar claves de licencia vinculadas a esa MAC
- Cifrar y descifrar el token de estado en disco
- Validar la licencia contra el servidor central (online) o contra el token local (offline)
- Detectar manipulación del token y retroceso del reloj del sistema

---

## 2. Componentes

### `LicenseResult` (dataclass)

Resultado devuelto por todas las operaciones de validación.

| Campo | Tipo | Descripción |
|---|---|---|
| `status` | str | Estado de la licencia (ver tabla de estados) |
| `message` | str | Mensaje legible para el usuario |
| `expiry_date` | datetime \| None | Fecha de vencimiento |
| `days_remaining` | int | Días hasta el vencimiento (0 si inválida) |
| `license_type` | str | `"commercial"` o `"trial"` |
| `offline_mode` | bool | `True` si la validación fue local (sin servidor) |
| `is_valid` | bool | `True` si status == "VALID" |

**Estados posibles:**

| Estado | Significado | Acción del middleware |
|---|---|---|
| `VALID` | Licencia activa y vigente | Permite el acceso |
| `NO_LICENSE` | No hay token en disco | Redirige a activación |
| `EXPIRED` | Vencida o límite offline superado | Redirige a página de vencimiento |
| `TAMPERED` | Token modificado o corrompido | Borra token, redirige a activación |
| `CLOCK_ROLLBACK` | Reloj del sistema retrocedido | Borra token, redirige a activación |

### `LicenseEngine` (clase principal)

Recibe toda su configuración en el constructor. No lee variables de entorno directamente — eso lo hace `engine_factory.py`.

```python
engine = LicenseEngine(
    secret_key=...,       # secreto compartido con el servidor
    token_path=...,       # ruta del archivo de token en disco
    server_url=...,       # URL base del servidor central
    api_key=...,          # X-License-Agent-Key
    max_offline_days=30,  # días máximos sin conexión
    http_timeout=5.0,     # timeout en segundos para llamadas HTTP
)
```

---

## 3. Operaciones del Motor

### 3.1 Obtención de MAC (`get_server_mac`)

Lee todas las interfaces de red mediante `psutil.net_if_addrs()`. Filtra:
- Interfaces de loopback (127.x.x.x)
- MACs nulas (`00:00:00:00:00:00`)
- Interfaces sin dirección de enlace (AF_LINK)

Devuelve la primera MAC válida normalizada: sin separadores, uppercase. Ejemplo: `AABBCCDDEEFF`.

Si no se encuentra ninguna NIC válida, lanza `RuntimeError`. Esto evita que el sistema opere en un entorno sin hardware de red real.

### 3.2 Generación de clave de licencia (`generate_key`)

```
clave = HMAC-SHA256(secret_key, f"{mac}:{nit}".encode() + VERSION_SALT)
      → base32 → primeros 20 caracteres → formato XXXX-XXXX-XXXX-XXXX
```

La clave es reproducible: el mismo servidor con el mismo NIT siempre produce la misma clave. Esto permite que el cliente la genere localmente y el servidor la verifique de forma independiente, sin necesidad de que el servidor "cree" la clave.

`VERSION_SALT` es una constante binaria en el código fuente. Cambiarla invalida todas las claves generadas con versiones anteriores del motor.

### 3.3 Verificación de clave (`verify_key`)

```python
hmac.compare_digest(expected_key, provided_key)
```

Usa `compare_digest` en lugar de `==` para resistir ataques de timing: el tiempo de comparación es constante independientemente de cuántos caracteres coincidan.

### 3.4 Derivación de la clave Fernet (`_derive_fernet_key`)

```
salt  = mac.encode()        # MAC normalizada como salt
key   = PBKDF2-HMAC-SHA256(
            password = secret_key,
            salt     = salt,
            iterations = 480_000,   # NIST SP 800-132 recomendado
            dklen    = 32
        )
fernet_key = base64url(key)
```

Con 480.000 iteraciones, un atacante que obtenga el archivo de token necesita computar el PBKDF2 para cada MAC candidata, haciendo el ataque por fuerza bruta impracticable incluso con hardware dedicado.

### 3.5 Guardado y carga del token (`save_token` / `load_token`)

El token es un diccionario JSON:

```json
{
    "license_key": "XXXX-XXXX-XXXX-XXXX",
    "nit": "900123456-7",
    "expiry": "2027-01-01T00:00:00+00:00",
    "license_type": "commercial",
    "last_online_check": "2026-06-19T10:30:00+00:00"
}
```

**Guardado:** el JSON se cifra con Fernet (clave derivada de la MAC) y se escribe en disco en `token_path`.

**Carga:** se lee el archivo, se descifra. Si el descifrado falla (archivo corrompido o MAC diferente), `load_token` devuelve la cadena `"TAMPERED"`. Si el archivo no existe, devuelve `None`.

Esta distinción — `None` vs `"TAMPERED"` — permite que el middleware diferencie entre "nunca se activó" y "alguien manipuló el token".

### 3.6 Validación online (`validate_online`)

Realiza un `POST` a `{server_url}/licenses/validate/` con:

```json
{
    "mac": "AABBCCDDEEFF",
    "license_key": "XXXX-XXXX-XXXX-XXXX",
    "nit": "900123456-7"
}
```

Header: `X-License-Agent-Key: <api_key>`

**Respuestas del servidor:**
- `200 OK` con `{"valid": true, "expiry_date": "...", "server_time": "..."}` → `VALID`
- `200 OK` con `{"valid": false}` → `EXPIRED`
- `403 Forbidden` → `EXPIRED` (licencia revocada)
- Cualquier error de red / timeout → devuelve `None` (activa el fallback offline)

Si `validate_online` devuelve `None`, el motor cae automáticamente a `validate_offline`. Si devuelve un resultado válido, actualiza el token en disco con la nueva fecha de vencimiento y el timestamp actual como `last_online_check`.

### 3.7 Validación offline (`validate_offline`)

Ejecutada cuando el servidor central no responde. Opera exclusivamente sobre el token local. Los controles se ejecutan en este orden estricto:

```
1. ¿now < last_online_check?
   → SÍ: CLOCK_ROLLBACK (reloj retrocedido, manipulación detectada)
   → NO: continúa

2. offline_days = (now - last_online_check).days
   ¿offline_days > max_offline_days?
   → SÍ: EXPIRED ("X días sin conexión, máximo N")
   → NO: continúa

3. ¿now > expiry?
   → SÍ: EXPIRED (licencia vencida)
   → NO: VALID (offline_mode=True)
```

El orden es deliberado: validar rollback antes que días offline evita que un reloj manipulado produzca conteos negativos. Validar días offline antes que vencimiento garantiza sincronización periódica con el servidor incluso si la licencia aún no ha vencido.

---

## 4. Flujo Principal: `validate()`

Llamado por el middleware en cada solicitud HTTP:

```
validate()
│
├─ 1. get_server_mac()
│      └─ RuntimeError si no hay NIC válida
│
├─ 2. load_token(mac)
│      ├─ None     → NO_LICENSE
│      └─ "TAMPERED" → TAMPERED
│
├─ 3. validate_online(mac, key, nit)
│      ├─ resultado online → actualiza token → retorna resultado
│      └─ None (sin red) → continúa a paso 4
│
└─ 4. validate_offline(token)
       └─ CLOCK_ROLLBACK | EXPIRED | VALID(offline)
```

---

## 5. Flujo de Activación: `activate_from_response()`

Llamado desde la vista Django tras una activación exitosa en el servidor central:

```python
token = {
    "license_key": self.generate_key(mac, nit),
    "nit": nit,
    "expiry": response_data["expiry_date"],
    "license_type": response_data["license_type"],
    "last_online_check": response_data["server_time"],  # ancla anti-rollback inicial
}
self.save_token(mac, token)
```

El campo `last_online_check` se inicializa con el tiempo del servidor central (no del cliente), estableciendo el primer ancla temporal confiable.

---

## 6. Seguridad

### Hardware-binding
El token es ilegible en cualquier servidor que no sea aquel donde se activó. Mover el archivo de token a otra máquina produce `TAMPERED` porque la MAC es distinta y la clave Fernet derivada no puede descifrar el contenido.

### Anti-rollback de reloj
El campo `last_online_check` actúa como ancla temporal. Al estar cifrado dentro del token Fernet, el usuario no puede modificarlo sin corromper el archivo. Si retrocede el reloj del sistema por debajo de este valor, la detección es inmediata.

### Integridad del token
Fernet incluye HMAC-SHA256 sobre el texto cifrado. Cualquier modificación del archivo — aunque sea de un bit — hace que el descifrado falle y el sistema devuelva `TAMPERED`.

### Resistencia a timing attacks
La verificación de claves usa `hmac.compare_digest`, que siempre tarda el mismo tiempo independientemente de cuántos caracteres coincidan.

---

## 7. Configuración

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `secret_key` | str | requerido | Secreto compartido para HMAC. Mínimo 32 caracteres aleatorios. |
| `token_path` | Path | requerido | Ruta absoluta del archivo de token en disco. |
| `server_url` | str | requerido | URL base del servidor central (sin barra final). |
| `api_key` | str | requerido | Valor del header `X-License-Agent-Key`. |
| `max_offline_days` | int | `30` | Días máximos sin conexión al servidor. |
| `http_timeout` | float | `5.0` | Timeout en segundos para llamadas HTTP. |

---

## 8. Pruebas

La suite cubre los siguientes casos con `unittest.TestCase` sin dependencias Django:

| Grupo | Casos cubiertos |
|---|---|
| `generate_key` | Formato correcto, reproducibilidad, distinción por NIT o MAC diferentes |
| `verify_key` | Clave correcta → True, clave incorrecta → False |
| `save_token / load_token` | Roundtrip completo, archivo corrupto → TAMPERED, archivo ausente → None |
| `validate_offline` | Rollback de reloj, límite offline exacto (30 días), límite superado (31 días), vencida, vigente, boundary del día de vencimiento, campo faltante |
| `validate` | Integración completa: online exitosa, fallback offline, TAMPERED, NO_LICENSE |

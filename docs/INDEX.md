# Sistema de Licencias de Software — Índice General

**Versión:** 1.0  
**Fecha:** 2026-06-19  
**Estado:** En revisión

---

## Resumen Ejecutivo

El Sistema de Licencias es una solución de control de acceso por software que restringe el uso de una aplicación Django a servidores autorizados y empresas con licencia vigente. Combina criptografía simétrica (Fernet / AES-128), firmas HMAC-SHA256 y vinculación al hardware del servidor (MAC de la NIC activa) para garantizar que una licencia activada solo opera en la máquina para la que fue emitida.

El sistema se compone de dos artefactos desplegables independientes:

| Artefacto | Rol | Ubicación |
|---|---|---|
| Motor embebido (Fases 1 + 2) | Se integra dentro de la aplicación cliente | `license_engine.py`, `license_middleware.py` |
| Servidor central (Fase 3) | API REST + panel admin | Servidor propio con PostgreSQL |

---

## Arquitectura General

```
┌─────────────────────────────────────────────────────────┐
│                   SERVIDOR DEL CLIENTE                  │
│                                                         │
│  ┌──────────────┐    ┌─────────────────────────────┐   │
│  │   Aplicación  │    │    Motor de Licencias        │   │
│  │    Django     │◄──►│  (LicenseEngine + Middleware)│   │
│  └──────────────┘    └──────────────┬──────────────┘   │
│                                     │                   │
│                               token cifrado             │
│                               (disco local)             │
└─────────────────────────────────────┼───────────────────┘
                                      │ HTTPS (validación periódica)
                                      ▼
┌─────────────────────────────────────────────────────────┐
│                  SERVIDOR CENTRAL                       │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐                  │
│  │   API REST    │    │    Admin     │                  │
│  │   (DRF)      │    │   (Django)   │                  │
│  └──────┬───────┘    └──────────────┘                  │
│         │                                               │
│  ┌──────▼───────────────────────────┐                  │
│  │  PostgreSQL (Client, License,    │                  │
│  │  AuditLog)                       │                  │
│  └──────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

---

## Fases del Proyecto

| Fase | Componente | Tecnología principal | Descripción |
|---|---|---|---|
| **Fase 1** | Motor criptográfico | Python, cryptography, psutil, httpx | Generación de claves, cifrado de token, validación online/offline |
| **Fase 2** | Middleware Django | Django middleware | Intercepta solicitudes HTTP, aplica restricciones por estado de licencia |
| **Fase 3** | Servidor central | Django, DRF, PostgreSQL, django-unfold | API REST de activación/validación, panel de administración |

---

## Modelo de Seguridad

El sistema ofrece cinco garantías de seguridad:

| Garantía | Mecanismo | Qué protege |
|---|---|---|
| **Hardware-binding** | Token cifrado con clave derivada de la MAC del servidor (PBKDF2, 480.000 iteraciones) | Impide copiar el token a otro servidor |
| **Cifrado en reposo** | Fernet (AES-128-CBC + HMAC-SHA256) | El token en disco es ilegible sin la MAC correcta |
| **Identidad HMAC** | `HMAC-SHA256(secret, mac + nit + VERSION_SALT)` → clave de 20 caracteres | Solo el servidor conocido puede generar una clave válida |
| **Anti-rollback de reloj** | Campo `last_online_check` en el token como ancla temporal | Detecta si el reloj del sistema fue retrocedido para evadir el vencimiento |
| **Auditoría inmutable** | `AuditLog` — sin permisos de edición ni eliminación en ningún rol | Trazabilidad completa de todas las operaciones |

---

## Requisitos de Infraestructura

### Motor embebido (instalado en el servidor cliente)

| Dependencia | Versión mínima | Uso |
|---|---|---|
| Python | 3.10+ | Runtime |
| Django | 4.2+ | Framework web |
| cryptography | 41.0+ | Fernet, PBKDF2 |
| psutil | 5.9+ | Lectura de MAC de la NIC |
| httpx | 0.24+ | Llamadas HTTP al servidor central |

### Servidor central

| Dependencia | Versión mínima | Uso |
|---|---|---|
| Python | 3.10+ | Runtime |
| Django | 4.2+ | Framework web |
| djangorestframework | 3.14+ | API REST |
| PostgreSQL | 14+ | Base de datos |
| django-unfold | 0.30+ | Panel de administración moderno |

---

## Documentación por Fase

- [Fase 1 — Motor Criptográfico](fase1-motor-criptografico.md)
- [Fase 2 — Middleware Django](fase2-middleware-django.md)
- [Fase 3 — Servidor Central](fase3-servidor-central.md)

---

## Glosario

| Término | Definición |
|---|---|
| **MAC** | Dirección física de la tarjeta de red del servidor (12 hex sin separadores, uppercase). Identifica unívocamente el hardware. |
| **NIT** | Número de Identificación Tributaria de la empresa cliente. Junto con la MAC forma la identidad única de cada licencia. |
| **Fernet** | Esquema de cifrado simétrico autenticado (AES-128-CBC + HMAC-SHA256) de la librería `cryptography`. Garantiza confidencialidad e integridad. |
| **HMAC** | Hash-based Message Authentication Code. Se usa para generar y verificar la clave de licencia vinculando MAC + NIT + secreto compartido. |
| **Token local** | Archivo cifrado en disco que almacena el estado de la licencia: clave, NIT, fecha de vencimiento, tipo y última validación online. |
| **Modo offline** | Operación sin conexión al servidor central. El motor valida contra el token local hasta el límite de días configurado (default: 30). |
| **Rollback de reloj** | Intento de retroceder el reloj del sistema operativo para evadir el vencimiento de la licencia. Detectado comparando `datetime.now()` con `last_online_check`. |
| **AgentKey** | Clave de API en el header `X-License-Agent-Key` que autentica al motor cliente ante el servidor central. |
| **VERSION_SALT** | Constante binaria en el código fuente que hace inválidas las claves generadas con versiones anteriores del motor. |

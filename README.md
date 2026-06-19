# Sistema de Licencias

Sistema de licenciamiento de software con servidor central de administración,
middleware de validación para apps cliente y un motor criptográfico offline.

## Arquitectura

El proyecto está dividido en tres componentes (fases):

| Fase | Componente | Ubicación | Descripción |
|------|------------|-----------|-------------|
| 1 | **Motor criptográfico** | `license_engine.py` | Generación/validación de licencias (Fernet + HMAC-SHA256), validación offline con anti-rollback de reloj. Independiente de Django. |
| 2 | **Middleware Django** | `license_system/` | Middleware que valida la licencia en cada request y redirige a activación si falta o vence. |
| 3 | **Servidor central** | `config/`, `licenses/` | API REST (DRF) + panel de administración (Unfold) para gestionar clientes, licencias y auditoría. |

## Requisitos

- Python 3.11+
- Para producción: PostgreSQL

## Instalación (desarrollo)

```bash
pip install -r requirements-dev.txt   # runtime + dependencias de pruebas
cp .env.example .env                  # y poner DEBUG=True para desarrollo
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Panel de administración: http://127.0.0.1:8000/admin/

## Configuración

Las variables se leen del entorno (o de un archivo `.env` local en desarrollo).
Ver `.env.example`. En **producción** (`DEBUG=False`) son obligatorias
`DJANGO_SECRET_KEY`, `LICENSE_SECRET_KEY` y `LICENSE_AGENT_API_KEY`: si faltan,
la aplicación no arranca (no usa valores por defecto inseguros).

## API

Todas requieren la cabecera `X-License-Agent-Key: <LICENSE_AGENT_API_KEY>`.

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/licenses/activate` | Activa una licencia comercial |
| POST | `/api/v1/licenses/validate` | Valida una licencia existente |
| POST | `/api/v1/licenses/trial` | Activa una prueba gratuita (30 días) |

## Pruebas

```bash
python -m pytest                 # suite completa (142 tests)
python -m pytest --cov=licenses  # con cobertura
```

## Despliegue (producción)

```bash
pip install -r requirements.txt
# Definir variables de entorno (no usar .env): DEBUG=False, DJANGO_SECRET_KEY,
# LICENSE_SECRET_KEY, LICENSE_AGENT_API_KEY, DATABASE_URL, ALLOWED_HOSTS
python manage.py migrate
python manage.py collectstatic --noinput
# Servir con un WSGI/ASGI de producción (gunicorn/uvicorn), no runserver.
```

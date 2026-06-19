"""
settings.py — Servidor Central de Licencias
Configuración de Django para el servidor que gestiona todas las licencias.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Seguridad ────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-cambiar-en-produccion")
DEBUG = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ── Apps ─────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    # Admin UI moderna
    "unfold",
    "unfold.contrib.filters",

    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # DRF
    "rest_framework",

    # App de licencias
    "licenses",
]

# ── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

# ── Templates ────────────────────────────────────────────────────────────────
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.debug",
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ],
    },
}]

WSGI_APPLICATION = "config.wsgi.application"

# ── Base de datos ────────────────────────────────────────────────────────────
# Producción: PostgreSQL via DATABASE_URL
# Desarrollo: SQLite local
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL:
    import dj_database_url
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ── DRF ──────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "license_activate": "10/hour",
    },
}

# ── Sistema de Licencias ─────────────────────────────────────────────────────
# CRÍTICO: debe ser la misma que LICENSE_SECRET_KEY en el proyecto cliente
LICENSE_SECRET_KEY = os.environ.get("LICENSE_SECRET_KEY", "CHANGE_IN_PRODUCTION")
VERSION_SALT = b"v1.0"

# API Key que deben enviar los agentes clientes
LICENSE_AGENT_API_KEY = os.environ.get("LICENSE_AGENT_API_KEY", "dev-agent-key-cambiar")

# Duración de licencias (días)
LICENSE_COMMERCIAL_DAYS = int(os.environ.get("LICENSE_COMMERCIAL_DAYS", "365"))
LICENSE_TRIAL_DAYS = int(os.environ.get("LICENSE_TRIAL_DAYS", "30"))

# ── Unfold Admin UI ──────────────────────────────────────────────────────────
# Helpers de permiso para la navegación: cada enlace se muestra solo si el
# operador puede realizar esa acción (view/add) sobre el modelo.
def _can(perm):
    return lambda request: request.user.has_perm(perm)


def _can_view(model):
    return lambda request: (
        request.user.has_perm(f"{model}") or request.user.has_perm(model.replace("view_", "change_"))
    )


UNFOLD = {
    "SITE_TITLE": "Servidor de Licencias",
    "SITE_HEADER": "Sistema de Licencias",
    "SITE_SUBHEADER": "Panel de Administración",
    "SITE_URL": "/",
    "SITE_SYMBOL": "key",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "DASHBOARD_CALLBACK": "licenses.dashboard.dashboard_callback",
    # Paleta teal — unifica changelists y formularios con la consola de credenciales.
    "COLORS": {
        "primary": {
            "50": "240 253 250",
            "100": "204 251 241",
            "200": "153 246 228",
            "300": "94 234 212",
            "400": "45 212 191",
            "500": "20 184 166",
            "600": "13 148 136",
            "700": "15 118 110",
            "800": "17 94 89",
            "900": "19 78 74",
            "950": "4 47 46",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "General",
                "items": [
                    {"title": "Inicio", "icon": "dashboard", "link": "/admin/"},
                ],
            },
            {
                "title": "Gestión",
                "items": [
                    {"title": "Clientes",  "icon": "business", "link": "/admin/licenses/client/",
                     "permission": _can_view("licenses.view_client")},
                    {"title": "Licencias", "icon": "key",      "link": "/admin/licenses/license/",
                     "permission": _can_view("licenses.view_license")},
                    {"title": "Usuarios",  "icon": "people",   "link": "/admin/auth/user/",
                     "permission": _can_view("auth.view_user")},
                ],
            },
            {
                "title": "Seguridad",
                "items": [
                    {"title": "Auditoría", "icon": "history", "link": "/admin/licenses/auditlog/",
                     "permission": _can_view("licenses.view_auditlog")},
                ],
            },
        ],
    },
}

# ── Internacionalización ─────────────────────────────────────────────────────
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

# ── Estáticos ────────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "licenses": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

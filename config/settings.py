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
UNFOLD = {
    "SITE_TITLE": "Servidor de Licencias",
    "SITE_HEADER": "Sistema de Licencias",
    "SITE_SUBHEADER": "Panel de Administración",
    "SITE_URL": "/",
    "SITE_SYMBOL": "key",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "COLORS": {
        "primary": {
            "50":  "240 249 255",
            "100": "224 242 254",
            "200": "186 230 253",
            "300": "125 211 252",
            "400": "56  189 248",
            "500": "14  165 233",
            "600": "2   132 199",
            "700": "3   105 161",
            "800": "7   89  133",
            "900": "12  74  110",
            "950": "8   47  73",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Licencias",
                "items": [
                    {"title": "Dashboard", "icon": "dashboard", "link": "/admin/"},
                    {"title": "Licencias", "icon": "key",       "link": "/admin/licenses/license/"},
                    {"title": "Clientes",  "icon": "business",  "link": "/admin/licenses/client/"},
                    {"title": "Audit Log", "icon": "history",   "link": "/admin/licenses/auditlog/"},
                ],
            },
            {
                "title": "Administración",
                "items": [
                    {"title": "Usuarios", "icon": "people", "link": "/admin/auth/user/"},
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

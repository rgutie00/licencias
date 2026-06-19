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

"""
dashboard.py — Contexto del panel de inicio del admin (Unfold DASHBOARD_CALLBACK).

Calcula el nivel de acceso del operador y la matriz de permisos CRUD por módulo,
de modo que el panel muestre exactamente lo que cada perfil puede hacer.
"""
from django.contrib.auth.models import User
from django.utils import timezone

from .models import AuditLog, Client, License


# Nivel de clearance derivado de los flags del usuario.
def _clearance(user):
    if user.is_superuser:
        return {"label": "Superusuario", "tagline": "Acceso total", "code": "super"}
    if user.is_staff:
        return {"label": "Administrador", "tagline": "Acceso de staff", "code": "staff"}
    return {"label": "Usuario", "tagline": "Acceso limitado", "code": "user"}


def _caps(user, app_label, model, *, can_add=True, can_change=True, can_delete=True):
    """Permisos CRUD reales del usuario para un modelo, respetando bloqueos del admin."""
    perm = f"{app_label}.{{}}_{model}"
    return {
        "view":   user.has_perm(perm.format("view")) or user.has_perm(perm.format("change")),
        "add":    can_add and user.has_perm(perm.format("add")),
        "change": can_change and user.has_perm(perm.format("change")),
        "delete": can_delete and user.has_perm(perm.format("delete")),
    }


def dashboard_callback(request, context):
    user = request.user
    now = timezone.now()

    modules = [
        {
            "name": "Clientes",
            "icon": "business",
            "url": "/admin/licenses/client/",
            "add_url": "/admin/licenses/client/add/",
            "caps": _caps(user, "licenses", "client"),
        },
        {
            "name": "Licencias",
            "icon": "key",
            "url": "/admin/licenses/license/",
            "add_url": "/admin/licenses/license/add/",
            "caps": _caps(user, "licenses", "license"),
        },
        {
            "name": "Usuarios",
            "icon": "people",
            "url": "/admin/auth/user/",
            "add_url": "/admin/auth/user/add/",
            "caps": _caps(user, "auth", "user"),
        },
        {
            # La auditoría es inmutable: solo lectura para todos.
            "name": "Auditoría",
            "icon": "history",
            "url": "/admin/licenses/auditlog/",
            "add_url": None,
            "caps": _caps(user, "licenses", "auditlog",
                          can_add=False, can_change=False, can_delete=False),
        },
    ]

    context.update({
        "lz_clearance": _clearance(user),
        "lz_user": user,
        "lz_now": now,
        "lz_modules": modules,
        "lz_stats": {
            "clients": Client.objects.count(),
            "active_licenses": License.objects.filter(
                status="active", expiry_date__gt=now).count(),
            "audit_events": AuditLog.objects.count(),
            "operators": User.objects.filter(is_staff=True).count(),
        },
    })
    return context

"""
admin.py — Panel de Administración del Servidor de Licencias.

Vistas:
    ClientAdmin  — gestión de empresas clientes
    LicenseAdmin — gestión de licencias (activar, revocar, extender)
    AuditLogAdmin — logs de auditoría (solo lectura)
"""
import logging

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin
from unfold.decorators import action

from django.urls import reverse

from .models import AuditLog, Client, License

logger = logging.getLogger("licenses")


# ── MIXIN: botones CRUD por fila (Editar / Borrar) ──────────────────────────

class RowActionsMixin:
    """Agrega una columna 'Acciones' con botones Editar y Borrar por fila,
    visibles solo si el operador tiene el permiso correspondiente."""

    def get_queryset(self, request):
        # Guardamos el request para evaluar permisos al renderizar los botones.
        self._request = request
        return super().get_queryset(request)

    @admin.display(description="Acciones")
    def acciones(self, obj):
        request = getattr(self, "_request", None)
        meta = obj._meta
        btns = []

        if request is None or self.has_change_permission(request, obj):
            url = reverse(f"admin:{meta.app_label}_{meta.model_name}_change", args=[obj.pk])
            btns.append(
                f'<a href="{url}" title="Editar" '
                f'style="display:inline-flex;align-items:center;gap:4px;padding:4px 10px;'
                f'margin-right:6px;border:1px solid #99F6E4;border-radius:8px;'
                f'color:#0F766E;font-size:12px;font-weight:600;text-decoration:none;">'
                f'<span class="material-symbols-outlined" style="font-size:15px;">edit</span>Editar</a>'
            )
        if request is None or self.has_delete_permission(request, obj):
            url = reverse(f"admin:{meta.app_label}_{meta.model_name}_delete", args=[obj.pk])
            confirm = "¿Borrar este registro? Esta acción no se puede deshacer."
            btns.append(
                f'<a href="{url}" title="Borrar" '
                f'onclick="return confirm(\'{confirm}\');" '
                f'style="display:inline-flex;align-items:center;gap:4px;padding:4px 10px;'
                f'border:1px solid #FECACA;border-radius:8px;'
                f'color:#DC2626;font-size:12px;font-weight:600;text-decoration:none;">'
                f'<span class="material-symbols-outlined" style="font-size:15px;">delete</span>Borrar</a>'
            )
        return mark_safe("".join(btns)) if btns else mark_safe('<span style="color:#94A3B8">—</span>')


# ── USUARIO (con estilos Unfold) ─────────────────────────────────────────────

class UserCreateForm(UserCreationForm):
    """Formulario de alta de usuario en un solo paso (con correo y nombres)."""
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name")


admin.site.unregister(User)

@admin.register(User)
class UserAdmin(RowActionsMixin, ModelAdmin, DjangoUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "acciones")

    # Alta en un solo paso: sin el mensaje de "dos pasos" de Django.
    add_form = UserCreateForm
    add_form_template = None
    add_fieldsets = (
        ("Identidad", {
            "classes": ("wide",),
            "fields": ("username", "email", "first_name", "last_name"),
        }),
        ("Contraseña", {
            "classes": ("wide",),
            "fields": ("password1", "password2"),
        }),
        ("Perfil y acceso", {
            "classes": ("wide",),
            "description": "Marca «staff» para permitir el acceso a este panel.",
            "fields": ("is_active", "is_staff", "groups"),
        }),
    )


# ── INLINE: Licencias dentro de Cliente ─────────────────────────────────────

class LicenseInline(admin.TabularInline):
    model = License
    extra = 0
    readonly_fields = [
        "id", "license_type", "status", "expiry_date",
        "activated_at", "days_remaining_display", "activated_by",
    ]
    fields = readonly_fields
    can_delete = False
    max_num = 0
    show_change_link = True
    verbose_name = "Licencia"
    verbose_name_plural = "Historial de licencias"

    def days_remaining_display(self, obj):
        d = obj.days_remaining
        if d == 0:
            return mark_safe('<span style="color:#ef4444">Vencida</span>')
        if d <= 7:
            return format_html('<span style="color:#f59e0b">⚠ {} días</span>', d)
        return format_html('<span style="color:#10b981">{} días</span>', d)
    days_remaining_display.short_description = "Días restantes"


# ── CLIENTE ──────────────────────────────────────────────────────────────────

@admin.register(Client)
class ClientAdmin(RowActionsMixin, ModelAdmin):
    list_display = [
        "name", "nit", "mac_short", "license_status_badge",
        "trial_used_display", "anomalies_count", "created_at", "acciones",
    ]
    list_filter  = ["trial_used", "created_at"]
    search_fields = ["name", "nit", "mac"]
    readonly_fields = ["id", "mac", "nit", "trial_used", "created_at", "updated_at"]
    ordering = ["-created_at"]
    inlines = [LicenseInline]

    def get_fieldsets(self, request, obj=None):
        if obj:  # Edición: mostrar la licencia activa
            return [
                ("Identificación", {"fields": ["id", "name", "nit", "mac"]}),
                ("Estado de licencia", {
                    "fields": ["license_status_badge", "trial_used", "anomalies_count"],
                }),
                ("Fechas", {"fields": ["created_at", "updated_at"]}),
            ]
        # Alta: aún no hay licencia ni fechas
        return [
            ("Identificación", {"fields": ["name", "nit", "mac"]}),
            ("Estado de licencia", {"fields": ["anomalies_count"]}),
        ]

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editando cliente existente — mac y nit son inmutables
            return ["id", "mac", "nit", "trial_used", "created_at", "updated_at",
                    "license_status_badge"]
        return ["id", "trial_used", "created_at", "updated_at"]  # Creando nuevo

    def mac_short(self, obj):
        return f"{obj.mac[:6]}..." if len(obj.mac) > 6 else obj.mac
    mac_short.short_description = "MAC"

    def license_status_badge(self, obj):
        lic = obj.active_license
        if not lic:
            return mark_safe('<span style="color:#ef4444;font-weight:700">Sin licencia activa</span>')
        d = lic.days_remaining
        color = "#10b981" if d > 7 else "#f59e0b" if d > 0 else "#ef4444"
        return format_html(
            '<span style="color:{};font-weight:700">{} — {} días</span>',
            color, lic.get_license_type_display(), d,
        )
    license_status_badge.short_description = "Licencia activa"

    def trial_used_display(self, obj):
        if obj.trial_used:
            return mark_safe('<span style="color:#f59e0b">✓ Usada</span>')
        return mark_safe('<span style="color:#64748b">Disponible</span>')
    trial_used_display.short_description = "Prueba"

    # Acción: activar licencia comercial de 1 año para clientes seleccionados
    @action(description="Activar licencia comercial (1 año)")
    def activate_manual(self, request, queryset):
        from datetime import timedelta

        from django.conf import settings
        from django.utils import timezone

        days = getattr(settings, "LICENSE_COMMERCIAL_DAYS", 365)
        count = 0
        for client in queryset:
            License.objects.filter(client=client, status="active").update(status="expired")
            expiry = timezone.now() + timedelta(days=days)
            lic = License.objects.create(
                client=client,
                license_type="commercial",
                status="active",
                expiry_date=expiry,
                activated_by=request.user,
            )
            AuditLog.log(
                action="MANUAL_ACTIVATE", result="success",
                license=lic, client=client, user=request.user,
                detail={"activated_by": request.user.username, "days": days},
            )
            count += 1
        self.message_user(request, f"{count} licencia(s) comercial(es) activadas (1 año).", messages.SUCCESS)

    # Acción: resetear trial_used (solo SuperAdmin)
    @action(description="Resetear prueba gratuita (Solo SuperAdmin)")
    def reset_trial(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Solo SuperAdmin puede resetear la prueba.", messages.ERROR)
            return

        count = queryset.count()
        for client in queryset:
            client.trial_used = False
            client.save(update_fields=["trial_used"])
            AuditLog.log(
                action="TRIAL_RESET", result="success",
                client=client, user=request.user,
                detail={"reset_by": request.user.username},
            )

        self.message_user(request, f"Prueba reseteada para {count} cliente(s).", messages.SUCCESS)
        logger.info("Trial reseteado por %s para %s clientes", request.user.username, count)


# ── LICENCIA ─────────────────────────────────────────────────────────────────

@admin.register(License)
class LicenseAdmin(RowActionsMixin, ModelAdmin):
    list_display = [
        "client", "license_type", "status_badge", "expiry_date",
        "days_remaining_display", "last_validated_at", "activated_at", "acciones",
    ]
    list_filter  = ["status", "license_type", "expiry_date"]
    search_fields = ["client__name", "client__nit", "client__mac"]
    readonly_fields = [
        "id", "client", "license_type", "activated_at",
        "activated_by", "last_validated_at", "revoked_at", "revoked_by",
    ]
    ordering = ["-activated_at"]

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editando licencia existente — client y license_type son inmutables
            return [
                "id", "client", "license_type", "activated_at",
                "activated_by", "last_validated_at", "revoked_at", "revoked_by",
                "status_badge", "days_remaining_display",
            ]
        return ["id", "activated_at", "activated_by", "last_validated_at", "revoked_at", "revoked_by"]

    def get_fieldsets(self, request, obj=None):
        if obj:  # Edición: mostrar estado actual y días restantes
            return [
                ("Estado actual", {
                    "fields": ["status_badge", "days_remaining_display"],
                }),
                ("Licencia", {
                    "fields": ["id", "client", "license_type", "status", "expiry_date"],
                }),
                ("Activación", {
                    "fields": ["activated_at", "activated_by", "last_validated_at"],
                }),
                ("Revocación", {
                    "fields": ["revoked_at", "revoked_by"],
                    "classes": ["collapse"],
                }),
                ("Notas", {"fields": ["notes"]}),
            ]
        # Alta: solo lo necesario para crear
        return [
            ("Licencia", {
                "fields": ["client", "license_type", "status", "expiry_date"],
            }),
            ("Notas", {"fields": ["notes"]}),
        ]

    def status_badge(self, obj):
        colors = {
            "active":  "#10b981",
            "expired": "#ef4444",
            "revoked": "#f59e0b",
            "pending": "#64748b",
        }
        color = colors.get(obj.status, "#64748b")
        return format_html(
            '<span style="color:{};font-weight:700">● {}</span>',
            color, obj.get_status_display(),
        )
    status_badge.short_description = "Estado"

    def days_remaining_display(self, obj):
        d = obj.days_remaining
        if obj.status != "active":
            return mark_safe('<span style="color:#64748b">—</span>')
        color = "#10b981" if d > 7 else "#f59e0b" if d > 0 else "#ef4444"
        return format_html('<span style="color:{}">{} días</span>', color, d)
    days_remaining_display.short_description = "Días restantes"

    # Acción: revocar licencias
    @action(description="Revocar licencias seleccionadas")
    def revoke_licenses(self, request, queryset):
        count = 0
        for lic in queryset.filter(status="active"):
            lic.revoke(user=request.user, note=f"Revocada desde panel por {request.user.username}")
            AuditLog.log(
                action="REVOKE", result="success",
                license=lic, client=lic.client,
                user=request.user,
                detail={"revoked_by": request.user.username},
            )
            count += 1

        self.message_user(request, f"{count} licencia(s) revocadas.", messages.SUCCESS)

    # Acción: extender 30 días
    @action(description="Extender 30 días")
    def extend_30_days(self, request, queryset):
        count = 0
        for lic in queryset.filter(status="active"):
            lic.expiry_date += timezone.timedelta(days=30)
            lic.save(update_fields=["expiry_date"])
            AuditLog.log(
                action="ACTIVATE", result="success",
                license=lic, client=lic.client,
                user=request.user,
                detail={"extended_days": 30, "by": request.user.username},
            )
            count += 1

        self.message_user(request, f"{count} licencia(s) extendidas 30 días.", messages.SUCCESS)



# ── AUDIT LOG ────────────────────────────────────────────────────────────────

@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = [
        "created_at", "action_badge", "client", "result_badge",
        "ip_address", "admin_user",
    ]
    list_filter  = ["action", "result", "created_at"]
    search_fields = ["client__name", "client__nit", "ip_address"]
    readonly_fields = [
        "action", "license", "client", "ip_address",
        "result", "detail", "admin_user", "created_at",
    ]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    # Audit log es solo lectura — nadie puede crear, editar ni eliminar
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def action_badge(self, obj):
        colors = {
            "ACTIVATE":        "#10b981",
            "VALIDATE":        "#00d4ff",
            "TRIAL_ACTIVATE":  "#b06cff",
            "REVOKE":          "#ef4444",
            "ANOMALY":         "#f59e0b",
            "MANUAL_ACTIVATE": "#10b981",
            "TRIAL_RESET":     "#f59e0b",
        }
        color = colors.get(obj.action, "#64748b")
        return format_html(
            '<span style="color:{};font-weight:700">{}</span>',
            color, obj.get_action_display(),
        )
    action_badge.short_description = "Acción"

    def result_badge(self, obj):
        colors = {
            "success":  "#10b981",
            "rejected": "#ef4444",
            "error":    "#f59e0b",
        }
        color = colors.get(obj.result, "#64748b")
        return format_html(
            '<span style="color:{};font-weight:700">{}</span>',
            color, obj.get_result_display(),
        )
    result_badge.short_description = "Resultado"


# ── Configuración del Admin Site ─────────────────────────────────────────────
admin.site.site_header = "Servidor de Licencias"
admin.site.site_title  = "Licencias Admin"
admin.site.index_title = "Panel de Administración"

"""
models.py — Modelos del servidor central de licencias.

Tablas:
    Client    — empresa cliente identificada por MAC + NIT
    License   — licencia activa, vencida o revocada
    AuditLog  — registro inmutable de todas las operaciones
"""
import uuid

from django.db import models
from django.utils import timezone


class Client(models.Model):
    """
    Empresa cliente identificada por la combinación MAC del servidor + NIT.
    Una vez creado, el NIT y MAC son inmutables para garantizar integridad.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Identificación del servidor del cliente
    mac = models.CharField(
        max_length=12,
        verbose_name="MAC del servidor",
        help_text="MAC normalizada: sin separadores, uppercase. Ej: AABBCCDDEEFF",
    )

    # Identificación de la empresa
    nit = models.CharField(
        max_length=20,
        verbose_name="NIT",
        help_text="NIT normalizado uppercase. Ej: 900123456-7",
    )
    name = models.CharField(
        max_length=200,
        verbose_name="Nombre de la empresa",
    )

    # Control de prueba — inmutable una vez en True
    trial_used = models.BooleanField(
        default=False,
        verbose_name="Prueba usada",
        help_text="Solo SuperAdmin puede resetear. Se registra en AuditLog.",
    )

    # Métricas de anomalías
    anomalies_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Anomalías detectadas",
        help_text="Rollbacks de reloj y tokens manipulados reportados.",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Registrado")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Actualizado")

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        unique_together = [("mac", "nit")]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["mac", "nit"]),
            models.Index(fields=["nit"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.nit})"

    @property
    def active_license(self):
        """Retorna la licencia activa vigente o None."""
        return self.licenses.filter(
            status="active",
            expiry_date__gt=timezone.now(),
        ).order_by("-activated_at").first()


class License(models.Model):
    """
    Licencia de software vinculada a un cliente.
    Una licencia activa por cliente a la vez.
    """

    TYPE_CHOICES = [
        ("commercial", "Comercial"),
        ("trial",      "Prueba gratuita"),
    ]

    STATUS_CHOICES = [
        ("active",   "Activa"),
        ("expired",  "Vencida"),
        ("revoked",  "Revocada"),
        ("pending",  "Pendiente"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="licenses",
        verbose_name="Cliente",
    )

    license_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="commercial",
        verbose_name="Tipo",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
        verbose_name="Estado",
    )

    expiry_date = models.DateTimeField(verbose_name="Vence el")
    activated_at = models.DateTimeField(auto_now_add=True, verbose_name="Activada")
    activated_by = models.ForeignKey(
        "auth.User",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="activated_licenses",
        verbose_name="Activada por (admin)",
        help_text="Solo se llena si la activación fue manual desde el panel.",
    )
    last_validated_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Última validación online",
    )
    revoked_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Revocada el",
    )
    revoked_by = models.ForeignKey(
        "auth.User",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="revoked_licenses",
        verbose_name="Revocada por",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notas",
        help_text="Observaciones del administrador.",
    )

    class Meta:
        verbose_name = "Licencia"
        verbose_name_plural = "Licencias"
        ordering = ["-activated_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["expiry_date"]),
            models.Index(fields=["client", "status"]),
        ]

    def __str__(self):
        return f"{self.client.name} — {self.get_license_type_display()} [{self.get_status_display()}]"

    @property
    def is_valid(self) -> bool:
        return self.status == "active" and self.expiry_date > timezone.now()

    @property
    def days_remaining(self) -> int:
        if not self.is_valid:
            return 0
        return max((self.expiry_date - timezone.now()).days, 0)

    def revoke(self, user=None, note=""):
        """Revoca la licencia y registra quién lo hizo."""
        self.status = "revoked"
        self.revoked_at = timezone.now()
        self.revoked_by = user
        if note:
            self.notes = f"{self.notes}\n[REVOCADA] {note}".strip()
        self.save()


class AuditLog(models.Model):
    """
    Registro inmutable de todas las operaciones del sistema.
    Nunca se edita ni elimina — solo se crea.
    """

    ACTION_CHOICES = [
        ("ACTIVATE",       "Activación"),
        ("VALIDATE",       "Validación"),
        ("TRIAL_ACTIVATE", "Prueba activada"),
        ("REVOKE",         "Revocación"),
        ("ANOMALY",        "Anomalía detectada"),
        ("MANUAL_ACTIVATE","Activación manual"),
        ("TRIAL_RESET",    "Reset de prueba"),
    ]

    RESULT_CHOICES = [
        ("success",  "Éxito"),
        ("rejected", "Rechazado"),
        ("error",    "Error"),
    ]

    # No tiene UUID — BIGINT autoincremental para queries rápidas
    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        verbose_name="Acción",
    )
    license = models.ForeignKey(
        License,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        verbose_name="Licencia",
    )
    client = models.ForeignKey(
        Client,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        verbose_name="Cliente",
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name="IP",
    )
    result = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
        default="success",
        verbose_name="Resultado",
    )
    detail = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Detalle",
        help_text="Datos adicionales del evento en formato JSON.",
    )
    admin_user = models.ForeignKey(
        "auth.User",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Usuario admin",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        verbose_name = "Registro de auditoría"
        verbose_name_plural = "Registros de auditoría"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["client", "created_at"]),
        ]

    def __str__(self):
        client_name = self.client.name if self.client else "?"
        return f"[{self.created_at:%d/%m/%Y %H:%M}] {self.get_action_display()} — {client_name} [{self.get_result_display()}]"

    @classmethod
    def log(cls, action, result="success", license=None,
            client=None, ip=None, detail=None, user=None):
        """Helper para crear un log en una línea."""
        return cls.objects.create(
            action=action,
            result=result,
            license=license,
            client=client,
            ip_address=ip,
            detail=detail or {},
            admin_user=user,
        )

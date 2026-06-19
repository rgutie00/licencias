"""
views.py — API REST del servidor central de licencias.

Endpoints:
    POST /api/v1/licenses/activate  — Activar licencia comercial
    POST /api/v1/licenses/validate  — Validar licencia en cada inicio
    POST /api/v1/licenses/trial     — Solicitar prueba gratuita 30 días
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditLog, Client, License
from .permissions import AgentKeyPermission
from .serializers import ActivateRequestSerializer, ValidateRequestSerializer
from .validators import verify_license_key

logger = logging.getLogger("licenses")


def get_client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


class ActivateLicenseView(APIView):
    """
    POST /api/v1/licenses/activate
    Activa una licencia comercial para un cliente.

    Flujo:
        1. Verificar API Key del agente
        2. Validar body (MAC, NIT, license_key)
        3. Verificar HMAC: license_key corresponde a MAC+NIT
        4. Buscar o crear cliente
        5. Crear o renovar licencia
        6. Registrar en AuditLog
        7. Retornar token de respuesta

    Request:
        { mac, nit, client_name, license_key, system_date }

    Response 200:
        { status, license_id, expiry_date, license_type, server_time, days_remaining }
    """

    permission_classes = [AgentKeyPermission]

    def post(self, request):
        ip = get_client_ip(request)

        # 1. Validar body
        serializer = ActivateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("Activate: body inválido | ip=%s errors=%s", ip, serializer.errors)
            return Response(
                {"error": "INVALID_REQUEST", "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        mac = data["mac"]
        nit = data["nit"]
        key = data["license_key"]

        # 2. Verificar HMAC
        if not verify_license_key(mac, nit, key):
            logger.warning("Activate: HMAC inválido | nit=%s ip=%s", nit, ip)
            AuditLog.log(
                action="ACTIVATE", result="rejected", ip=ip,
                detail={"reason": "INVALID_KEY", "nit": nit, "mac": mac[:6]},
            )
            return Response(
                {"error": "INVALID_KEY", "message": "La clave de licencia no corresponde a este cliente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Buscar o crear cliente
        client, created = Client.objects.get_or_create(
            mac=mac, nit=nit,
            defaults={"name": data["client_name"]},
        )
        if not created and data["client_name"] and client.name != data["client_name"]:
            client.name = data["client_name"]
            client.save(update_fields=["name"])

        # 4. Revocar licencias activas previas (renovación)
        License.objects.filter(client=client, status="active").update(status="expired")

        # 5. Crear nueva licencia comercial
        days = getattr(settings, "LICENSE_COMMERCIAL_DAYS", 365)
        expiry = timezone.now() + timedelta(days=days)
        lic = License.objects.create(
            client=client,
            license_type="commercial",
            status="active",
            expiry_date=expiry,
            last_validated_at=timezone.now(),
        )

        # 6. Audit log
        AuditLog.log(
            action="ACTIVATE", result="success",
            license=lic, client=client, ip=ip,
            detail={"type": "commercial", "days": days},
        )

        logger.info("Licencia activada | nit=%s mac=%s... days=%s", nit, mac[:6], days)

        return Response({
            "status": "activated",
            "license_id": str(lic.id),
            "expiry_date": lic.expiry_date.isoformat(),
            "license_type": lic.license_type,
            "server_time": timezone.now().isoformat(),
            "days_remaining": days,
        }, status=status.HTTP_200_OK)


class ValidateLicenseView(APIView):
    """
    POST /api/v1/licenses/validate
    Valida una licencia en cada inicio del software.

    Flujo:
        1. Verificar API Key
        2. Validar body
        3. Verificar HMAC
        4. Buscar licencia activa del cliente
        5. Actualizar last_validated_at
        6. Retornar estado

    Response 200 (válida):
        { valid: true, status, expiry_date, server_time, days_remaining, license_type }

    Response 200 (inválida):
        { valid: false, status: "expired"|"revoked", ... }
    """

    permission_classes = [AgentKeyPermission]

    def post(self, request):
        ip = get_client_ip(request)

        serializer = ValidateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "INVALID_REQUEST", "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        mac = data["mac"]
        nit = data.get("nit", "")
        key = data["license_key"]

        # Verificar HMAC si hay NIT disponible
        if nit and not verify_license_key(mac, nit, key):
            logger.warning("Validate: HMAC inválido | nit=%s ip=%s", nit, ip)
            AuditLog.log(
                action="VALIDATE", result="rejected", ip=ip,
                detail={"reason": "INVALID_KEY", "mac": mac[:6]},
            )
            return Response(
                {"valid": False, "status": "invalid_key",
                 "server_time": timezone.now().isoformat()},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Buscar cliente
        try:
            client = Client.objects.get(mac=mac, nit=nit) if nit else Client.objects.get(mac=mac)
        except Client.DoesNotExist:
            return Response(
                {"valid": False, "status": "not_found",
                 "server_time": timezone.now().isoformat()},
                status=status.HTTP_200_OK,
            )
        except Client.MultipleObjectsReturned:
            client = Client.objects.filter(mac=mac).order_by("-created_at").first()

        # Buscar licencia activa
        lic = client.licenses.filter(
            status="active",
            expiry_date__gt=timezone.now(),
        ).order_by("-activated_at").first()

        if not lic:
            # Verificar si hay licencia revocada o vencida
            any_lic = client.licenses.order_by("-activated_at").first()
            lic_status = any_lic.status if any_lic else "not_found"

            AuditLog.log(
                action="VALIDATE", result="rejected",
                client=client, ip=ip,
                detail={"reason": lic_status},
            )
            return Response({
                "valid": False,
                "status": lic_status,
                "expiry_date": any_lic.expiry_date.isoformat() if any_lic else None,
                "server_time": timezone.now().isoformat(),
                "days_remaining": 0,
                "license_type": any_lic.license_type if any_lic else "",
            }, status=status.HTTP_200_OK)

        # Actualizar última validación
        lic.last_validated_at = timezone.now()
        lic.save(update_fields=["last_validated_at"])

        AuditLog.log(
            action="VALIDATE", result="success",
            license=lic, client=client, ip=ip,
        )

        return Response({
            "valid": True,
            "status": "active",
            "expiry_date": lic.expiry_date.isoformat(),
            "server_time": timezone.now().isoformat(),
            "days_remaining": lic.days_remaining,
            "license_type": lic.license_type,
        }, status=status.HTTP_200_OK)


class TrialLicenseView(APIView):
    """
    POST /api/v1/licenses/trial
    Solicita una licencia de prueba gratuita de 30 días.

    Reglas:
        - Solo UNA prueba por cliente (MAC + NIT)
        - Duración fija: 30 días
        - No prorrogable
        - trial_used se marca como True e inmutable

    Response 200: primera vez → trial_activated
    Response 409: ya usó la prueba → TRIAL_ALREADY_USED
    """

    permission_classes = [AgentKeyPermission]

    def post(self, request):
        ip = get_client_ip(request)

        serializer = ActivateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "INVALID_REQUEST", "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        mac = data["mac"]
        nit = data["nit"]
        key = data["license_key"]

        # Verificar HMAC
        if not verify_license_key(mac, nit, key):
            logger.warning("Trial: HMAC inválido | nit=%s ip=%s", nit, ip)
            return Response(
                {"error": "INVALID_KEY", "message": "Clave de licencia inválida."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar o crear cliente
        client, _ = Client.objects.get_or_create(
            mac=mac, nit=nit,
            defaults={"name": data["client_name"]},
        )

        # Regla de negocio: una sola prueba
        if client.trial_used:
            logger.info("Trial rechazado: ya usado | nit=%s", nit)
            AuditLog.log(
                action="TRIAL_ACTIVATE", result="rejected",
                client=client, ip=ip,
                detail={"reason": "TRIAL_ALREADY_USED"},
            )
            return Response(
                {
                    "error": "TRIAL_ALREADY_USED",
                    "message": "Este cliente ya utilizó su período de prueba gratuito.",
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Crear licencia de prueba
        days = getattr(settings, "LICENSE_TRIAL_DAYS", 30)
        expiry = timezone.now() + timedelta(days=days)

        lic = License.objects.create(
            client=client,
            license_type="trial",
            status="active",
            expiry_date=expiry,
            last_validated_at=timezone.now(),
        )

        # Marcar trial_used como True — inmutable desde ahora
        client.trial_used = True
        client.save(update_fields=["trial_used"])

        AuditLog.log(
            action="TRIAL_ACTIVATE", result="success",
            license=lic, client=client, ip=ip,
            detail={"days": days},
        )

        logger.info("Trial activado | nit=%s mac=%s... days=%s", nit, mac[:6], days)

        return Response({
            "status": "trial_activated",
            "license_id": str(lic.id),
            "expiry_date": lic.expiry_date.isoformat(),
            "license_type": "trial",
            "server_time": timezone.now().isoformat(),
            "days_remaining": days,
        }, status=status.HTTP_200_OK)

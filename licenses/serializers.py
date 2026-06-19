"""
serializers.py — Serializers DRF para los endpoints de licencias.
"""
from rest_framework import serializers


class ActivateRequestSerializer(serializers.Serializer):
    """Body del POST /licenses/activate y /licenses/trial"""
    mac         = serializers.CharField(max_length=17)
    nit         = serializers.CharField(max_length=20)
    client_name = serializers.CharField(max_length=200)
    license_key = serializers.CharField(max_length=20)
    system_date = serializers.DateTimeField(required=False)

    def validate_mac(self, value):
        cleaned = value.replace(":", "").replace("-", "").replace(".", "").upper().strip()
        if len(cleaned) != 12:
            raise serializers.ValidationError("MAC inválida. Debe tener 12 caracteres hex.")
        return cleaned

    def validate_nit(self, value):
        return value.strip().upper()

    def validate_license_key(self, value):
        value = value.strip().upper()
        parts = value.split("-")
        if len(parts) != 4 or not all(len(p) == 4 for p in parts):
            raise serializers.ValidationError(
                "Formato de clave inválido. Esperado: XXXX-XXXX-XXXX-XXXX"
            )
        return value


class ValidateRequestSerializer(serializers.Serializer):
    """Body del POST /licenses/validate"""
    mac         = serializers.CharField(max_length=17)
    nit         = serializers.CharField(max_length=20, required=False, default="")
    license_key = serializers.CharField(max_length=20)
    system_date = serializers.DateTimeField(required=False)

    def validate_mac(self, value):
        return value.replace(":", "").replace("-", "").replace(".", "").upper().strip()

    def validate_license_key(self, value):
        return value.strip().upper()


class LicenseResponseSerializer(serializers.Serializer):
    """Respuesta estándar de activación."""
    status       = serializers.CharField()
    license_id   = serializers.CharField()
    expiry_date  = serializers.DateTimeField()
    license_type = serializers.CharField()
    server_time  = serializers.DateTimeField()
    days_remaining = serializers.IntegerField()


class ValidateResponseSerializer(serializers.Serializer):
    """Respuesta estándar de validación."""
    valid          = serializers.BooleanField()
    status         = serializers.CharField()
    expiry_date    = serializers.DateTimeField(allow_null=True)
    server_time    = serializers.DateTimeField()
    days_remaining = serializers.IntegerField()
    license_type   = serializers.CharField()

"""
views.py — Vistas del flujo de activación de licencia.

  /license/activate/  → formulario de activación (GET/POST)
  /license/expired/   → pantalla de licencia vencida
  /license/success/   → confirmación tras activación exitosa
"""
from datetime import datetime, timezone

import httpx
from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .engine_factory import get_engine


def _render_activate(request, *, error=None, reason=""):
    return render(
        request,
        "license/activate.html",
        {
            "error": error,
            "reason": reason,
            "form_data": request.POST if request.method == "POST" else {},
        },
    )


@csrf_exempt
def activate(request):
    reason = request.GET.get("reason", "")

    if request.method != "POST":
        return _render_activate(request, reason=reason)

    nit = request.POST.get("nit", "").strip()
    client_name = request.POST.get("client_name", "").strip()
    license_type = request.POST.get("license_type", "commercial").strip() or "commercial"

    if not nit:
        return _render_activate(request, error="NIT es obligatorio.", reason=reason)

    if not client_name:
        return _render_activate(
            request,
            error="El nombre del cliente es obligatorio.",
            reason=reason,
        )

    server_url = getattr(settings, "LICENSE_SERVER_URL", "")
    if not server_url:
        return _render_activate(
            request,
            error="El servidor de licencias no está configurado. Contacte al administrador.",
            reason=reason,
        )

    engine = get_engine()
    mac = engine.get_server_mac()
    license_key = engine.generate_key(mac, nit)

    payload = {
        "mac": mac,
        "nit": nit.upper(),
        "client_name": client_name,
        "license_key": license_key,
        "license_type": license_type,
        "system_date": datetime.now(timezone.utc).isoformat(),
    }
    headers = {"X-License-Agent-Key": getattr(settings, "LICENSE_API_KEY", "")}
    endpoint = f"{server_url.rstrip('/')}/licenses/activate"

    try:
        response = httpx.post(endpoint, json=payload, headers=headers, timeout=10.0)
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError):
        return _render_activate(
            request,
            error="Sin conexión al servidor de licencias. Verifique su red e intente nuevamente.",
            reason=reason,
        )

    if response.status_code == 200:
        data = response.json()
        engine.activate_from_response(mac, nit, data)
        return HttpResponseRedirect("/license/success/")

    if response.status_code == 409:
        return _render_activate(
            request,
            error="Esta licencia de prueba ya fue usada para este servidor. Solicite una licencia comercial.",
            reason=reason,
        )

    if response.status_code == 403:
        return _render_activate(
            request,
            error="El servidor rechazó la activación (403). Verifique sus credenciales.",
            reason=reason,
        )

    return _render_activate(
        request,
        error=f"El servidor respondió con un error (HTTP {response.status_code}).",
        reason=reason,
    )


def expired(request):
    return render(request, "license/expired.html", {})


def success(request):
    return render(request, "license/success.html", {})

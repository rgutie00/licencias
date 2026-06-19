# Graph Report - .  (2026-06-19)

## Corpus Check
- Corpus is ~13,376 words - fits in a single context window. You may not need a graph.

## Summary
- 455 nodes · 730 edges · 31 communities (19 shown, 12 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 119 edges (avg confidence: 0.58)
- Token cost: 3,200 input · 1,100 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Client Model & Middleware Tests|Client Model & Middleware Tests]]
- [[_COMMUNITY_License System Django App Core|License System Django App Core]]
- [[_COMMUNITY_License Engine Unit Tests|License Engine Unit Tests]]
- [[_COMMUNITY_Root License Engine|Root License Engine]]
- [[_COMMUNITY_Central API Views & Serializers|Central API Views & Serializers]]
- [[_COMMUNITY_Token Storage & Validate Tests|Token Storage & Validate Tests]]
- [[_COMMUNITY_License Validators & API Tests|License Validators & API Tests]]
- [[_COMMUNITY_Activate & Trial Endpoint Tests|Activate & Trial Endpoint Tests]]
- [[_COMMUNITY_Templates & Dependencies|Templates & Dependencies]]
- [[_COMMUNITY_License Middleware & IP Handling|License Middleware & IP Handling]]
- [[_COMMUNITY_Offline Validation Tests|Offline Validation Tests]]
- [[_COMMUNITY_Admin & Audit Log Models|Admin & Audit Log Models]]
- [[_COMMUNITY_License Model|License Model]]
- [[_COMMUNITY_Model Unit Tests|Model Unit Tests]]
- [[_COMMUNITY_Validate Endpoint Tests|Validate Endpoint Tests]]
- [[_COMMUNITY_Audit Log Admin Panel|Audit Log Admin Panel]]
- [[_COMMUNITY_Client Admin Panel|Client Admin Panel]]
- [[_COMMUNITY_License Admin Panel|License Admin Panel]]
- [[_COMMUNITY_Django App Configuration|Django App Configuration]]
- [[_COMMUNITY_License System Middleware|License System Middleware]]
- [[_COMMUNITY_URL Routing Tests|URL Routing Tests]]
- [[_COMMUNITY_Test Configuration|Test Configuration]]
- [[_COMMUNITY_License System URLs|License System URLs]]
- [[_COMMUNITY_Django Settings|Django Settings]]
- [[_COMMUNITY_Project URL Config|Project URL Config]]
- [[_COMMUNITY_Artifact URL Config|Artifact URL Config]]

## God Nodes (most connected - your core abstractions)
1. `Client` - 44 edges
2. `LicenseEngine` - 29 edges
3. `LicenseResult` - 25 edges
4. `mock_engine()` - 23 edges
5. `License` - 22 edges
6. `AuditLog` - 20 edges
7. `LicenseEngine` - 19 edges
8. `activation_payload()` - 17 edges
9. `LicenseMiddleware` - 14 edges
10. `TestActivateEndpoint` - 14 edges

## Surprising Connections (you probably didn't know these)
- `Activate License Page (Root)` --semantically_similar_to--> `Activate License Template (Django)`  [INFERRED] [semantically similar]
  activate.html → license_system/templates/license/activate.html
- `Expired License Page (Root)` --semantically_similar_to--> `Expired License Template (Django)`  [INFERRED] [semantically similar]
  expired.html → license_system/templates/license/expired.html
- `License Activated Success Page (Root)` --semantically_similar_to--> `License Activated Success Template (Django)`  [INFERRED] [semantically similar]
  success.html → license_system/templates/license/success.html
- `LicenseEngine` --uses--> `LicenseEngine`  [INFERRED]
  engine_factory.py → license_engine.py
- `TestTokenStorage` --uses--> `LicenseResult`  [INFERRED]
  test_license_engine.py → license_engine.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **License Activation UI Flow (activate → success / expired)** — template_activate_activate_template, template_success_success_template, template_expired_expired_template [EXTRACTED 1.00]
- **Fase 1 Cryptographic License Engine** — req_fase1_license_engine, dep_cryptography, dep_psutil [EXTRACTED 1.00]
- **Fase 3 Central License Server Stack** — req_fase3_central_server, dep_django, dep_drf [EXTRACTED 1.00]

## Communities (31 total, 12 thin omitted)

### Community 0 - "Client Model & Middleware Tests"
Cohesion: 0.06
Nodes (28): Client, Empresa cliente identificada por la combinación MAC del servidor + NIT.     Una, Retorna la licencia activa vigente o None., make_result(), mock_engine(), test_middleware_views.py — Fase 2 Tests de integración del LicenseMiddleware y l, Las rutas /api/ también están protegidas., /accounts/login/ también está protegida — sin licencia no hay login. (+20 more)

### Community 1 - "License System Django App Core"
Cohesion: 0.06
Nodes (33): get_engine(), LicenseEngine, engine_factory.py — Fábrica singleton del LicenseEngine.  El engine se construye, Devuelve el singleton del LicenseEngine, creándolo si hace falta., Limpia el singleton. Usado por los tests., reset_engine(), LicenseEngine, LicenseResult (+25 more)

### Community 2 - "License Engine Unit Tests"
Cohesion: 0.05
Nodes (16): LicenseResult, bool, Resultado de una validación de licencia.      status posibles:         VALID, engine(), future_check(), test_license_engine.py — Fase 1 Tests unitarios del LicenseEngine.  Cómo ejecuta, Distintos formatos de MAC deben producir la misma clave., NIT con espacios y minúsculas debe dar la misma clave. (+8 more)

### Community 3 - "Root License Engine"
Cohesion: 0.07
Nodes (27): get_engine(), LicenseEngine, engine_factory.py — Fase 2 Crea y mantiene una instancia singleton del LicenseEn, Retorna el singleton del LicenseEngine.     Se crea la primera vez que se llama,, Reinicia el singleton. Útil en tests para forzar     reconfiguración con setting, reset_engine(), LicenseEngine, bytes (+19 more)

### Community 4 - "Central API Views & Serializers"
Cohesion: 0.08
Nodes (28): APIView, BasePermission, AgentKeyPermission, hmac_compare(), bool, str, permissions.py — Autenticación de agentes clientes. Los clientes se autentican c, Verifica que el request tenga el header X-License-Agent-Key correcto.     Se apl (+20 more)

### Community 5 - "Token Storage & Validate Tests"
Cohesion: 0.08
Nodes (11): make_token(), Token cifrado con MAC_A no se puede descifrar con MAC_B., Archivo con bytes aleatorios debe retornar TAMPERED., Archivo con JSON sin cifrar debe retornar TAMPERED., Eliminar token inexistente no debe lanzar error., Todos los campos del payload deben sobrevivir el cifrado/descifrado., Si el servidor responde OK, el token local debe actualizarse., Si el servidor no responde, debe usar validación offline. (+3 more)

### Community 6 - "License Validators & API Tests"
Cohesion: 0.12
Nodes (15): generate_license_key(), normalize_mac(), normalize_nit(), bool, str, validators.py — Validación HMAC server-side. El servidor regenera la clave esper, Normaliza MAC: sin separadores, uppercase., Normaliza NIT: sin espacios, uppercase. (+7 more)

### Community 7 - "Activate & Trial Endpoint Tests"
Cohesion: 0.17
Nodes (3): activation_payload(), TestActivateEndpoint, TestTrialEndpoint

### Community 8 - "Templates & Dependencies"
Cohesion: 0.15
Nodes (18): Activate License Page (Root), License Activation Flow, License State Machine (active/expired/tampered/clock-skew), License Tamper and Clock-Skew Detection, cryptography==42.0.8, Django==5.1.2, django-unfold==0.40.0 (Modern Admin UI), djangorestframework==3.15.2 (+10 more)

### Community 9 - "License Middleware & IP Handling"
Cohesion: 0.18
Nodes (7): LicenseMiddleware, bool, str, Retorna True si la ruta no necesita validación de licencia., Extrae la IP real del cliente (considera proxies)., Middleware de validación de licencias.      Se instancia una sola vez al arranca, TestMiddlewareIPExtraction

### Community 10 - "Offline Validation Tests"
Cohesion: 0.14
Nodes (6): Si last_check está en el futuro, el reloj fue retrocedido., Más días offline que el máximo permitido → EXPIRED., Exactamente en el límite de días offline → VALID., Licencia que vence exactamente hoy (futuro cercano) → VALID., Token sin campo expiry debe retornar EXPIRED., TestValidateOffline

### Community 11 - "Admin & Audit Log Models"
Cohesion: 0.20
Nodes (7): LicenseInline, admin.py — Panel de Administración del Servidor de Licencias.  Vistas:     Clien, AuditLog, Meta, models.py — Modelos del servidor central de licencias.  Tablas:     Client    —, Registro inmutable de todas las operaciones del sistema.     Nunca se edita ni e, Helper para crear un log en una línea.

### Community 12 - "License Model"
Cohesion: 0.22
Nodes (5): License, bool, int, Revoca la licencia y registra quién lo hizo., Licencia de software vinculada a un cliente.     Una licencia activa por cliente

### Community 18 - "Django App Configuration"
Cohesion: 0.40
Nodes (3): AppConfig, LicenseSystemConfig, LicensesConfig

## Knowledge Gaps
- **17 isolated node(s):** `int`, `float`, `bytes`, `bool`, `int` (+12 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Client` connect `Client Model & Middleware Tests` to `Central API Views & Serializers`, `License Validators & API Tests`, `Activate & Trial Endpoint Tests`, `Admin & Audit Log Models`, `Model Unit Tests`, `Validate Endpoint Tests`, `Audit Log Admin Panel`, `Client Admin Panel`, `License Admin Panel`?**
  _High betweenness centrality (0.400) - this node is a cross-community bridge._
- **Why does `LicenseResult` connect `License Engine Unit Tests` to `Client Model & Middleware Tests`, `Root License Engine`, `Token Storage & Validate Tests`, `License Middleware & IP Handling`, `Offline Validation Tests`?**
  _High betweenness centrality (0.357) - this node is a cross-community bridge._
- **Why does `TestMiddlewareBlocking` connect `Client Model & Middleware Tests` to `License Middleware & IP Handling`, `License Engine Unit Tests`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Are the 36 inferred relationships involving `Client` (e.g. with `AuditLogAdmin` and `ClientAdmin`) actually correct?**
  _`Client` has 36 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `LicenseEngine` (e.g. with `LicenseEngine` and `TestActivateFromResponse`) actually correct?**
  _`LicenseEngine` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `LicenseResult` (e.g. with `TestActivateFromResponse` and `TestActivationPayload`) actually correct?**
  _`LicenseResult` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `License` (e.g. with `AuditLogAdmin` and `ClientAdmin`) actually correct?**
  _`License` has 13 INFERRED edges - model-reasoned connections that need verification._
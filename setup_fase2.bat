@echo off
REM ══════════════════════════════════════════════════════════
REM  setup_fase2.bat
REM  Crea la estructura completa del proyecto desde cero.
REM  Ejecutar desde: C:\desarrollos\licencias\
REM ══════════════════════════════════════════════════════════

echo.
echo  ================================================
echo   SETUP FASE 2 - Creando estructura del proyecto
echo  ================================================
echo.

REM Mostrar donde estamos
echo  Directorio actual:
cd
echo.

REM Crear carpetas
echo  [1/3] Creando estructura de carpetas...

mkdir license_system 2>nul
mkdir license_system\templates 2>nul
mkdir license_system\templates\license 2>nul

echo  [OK] Carpetas creadas:
echo       license_system\
echo       license_system\templates\
echo       license_system\templates\license\
echo.

REM Verificar que license_engine.py existe en algún lado
echo  [2/3] Buscando license_engine.py...

if exist "license_engine.py" (
    echo  [OK] Encontrado en raiz.
    copy /Y "license_engine.py" "license_system\license_engine.py" >nul
    echo  [OK] Copiado a license_system\license_engine.py
    goto :check_other_files
)

if exist "license_system\license_engine.py" (
    echo  [OK] Ya existe en license_system\
    goto :check_other_files
)

REM No encontrado — listar todo para diagnóstico
echo  [WARN] license_engine.py no encontrado automaticamente.
echo.
echo  Archivos en el directorio actual:
dir /b
echo.
echo  Debes copiar manualmente license_engine.py a:
echo    C:\desarrollos\licencias\license_system\license_engine.py
echo.

:check_other_files
REM Verificar los demás archivos clave de fase 2
echo  [3/3] Verificando archivos de Fase 2...
echo.

set MISSING=0

for %%F in (
    "license_system\__init__.py"
    "license_system\apps.py"
    "license_system\engine_factory.py"
    "license_system\license_middleware.py"
    "license_system\views.py"
    "license_system\urls.py"
    "license_system\templates\license\activate.html"
    "license_system\templates\license\expired.html"
    "license_system\templates\license\success.html"
    "conftest.py"
    "test_urls.py"
    "test_middleware_views.py"
) do (
    if exist %%F (
        echo  [OK] %%F
    ) else (
        echo  [FALTA] %%F
        set MISSING=1
    )
)

echo.
if "%MISSING%"=="1" (
    echo  ================================================
    echo   Algunos archivos faltan.
    echo   Descargalos desde Claude y colocalos segun
    echo   la ruta indicada arriba con [FALTA].
    echo  ================================================
) else (
    echo  ================================================
    echo   Todos los archivos estan en su lugar.
    echo   Ejecuta: run_tests_fase2.bat
    echo  ================================================
)

echo.
pause

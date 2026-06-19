@echo off
REM ══════════════════════════════════════════════════════════
REM  run_tests_fase2.bat — v2
REM  Ejecutar desde: C:\desarrollos\licencias\
REM ══════════════════════════════════════════════════════════

echo.
echo  ================================================
echo   SISTEMA DE LICENCIAS - FASE 2 - TESTS
echo  ================================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no encontrado.
    pause & exit /b 1
)
echo  [OK] Python detectado.

REM Instalar dependencias
echo.
echo  [1/3] Instalando dependencias...
pip install pytest pytest-django psutil httpx cryptography -q
echo  [OK] Dependencias listas.

REM Copiar license_engine.py si no esta en license_system
echo.
echo  [2/3] Verificando license_engine.py en license_system\...

if exist "license_system\license_engine.py" (
    echo  [OK] license_engine.py ya existe en license_system\
    goto :run_tests
)

if exist "license_engine.py" (
    copy /Y "license_engine.py" "license_system\license_engine.py" >nul
    echo  [OK] Copiado desde raiz.
    goto :run_tests
)

echo  [ERROR] No se encontro license_engine.py
echo  Coloca license_engine.py en C:\desarrollos\licencias\
pause & exit /b 1

:run_tests
echo.
echo  [3/3] Ejecutando tests...
echo.

pytest test_middleware_views.py -v --tb=short -p no:warnings

echo.
if errorlevel 1 (
    echo  ================================================
    echo   [FALLO] Algunos tests fallaron.
    echo  ================================================
) else (
    echo  ================================================
    echo   [OK] Todos los tests de Fase 2 pasaron.
    echo        Listo para Fase 3 - Servidor Central
    echo  ================================================
)
echo.
pause

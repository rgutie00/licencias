@echo off
REM ══════════════════════════════════════════════════════════
REM  run_tests.bat — Fase 1: License Engine
REM  Ejecutar desde: C:\desarrollos\licencias\
REM ══════════════════════════════════════════════════════════

echo.
echo  ================================================
echo   SISTEMA DE LICENCIAS — FASE 1 — TESTS
echo  ================================================
echo.

REM Verificar que Python esté disponible
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no encontrado. Instala Python 3.11+
    pause
    exit /b 1
)

REM Instalar dependencias si no están
echo  [1/3] Instalando dependencias...
pip install -r requirements-dev.txt -q
if errorlevel 1 (
    echo  [ERROR] Falló la instalación de dependencias.
    pause
    exit /b 1
)
echo  [OK] Dependencias instaladas.
echo.

REM Ejecutar tests con cobertura
echo  [2/3] Ejecutando tests...
echo.
pytest test_license_engine.py -v --tb=short --cov=license_engine --cov-report=term-missing
echo.

REM Resultado
if errorlevel 1 (
    echo  ================================================
    echo   [FALLO] Algunos tests fallaron. Revisa arriba.
    echo  ================================================
) else (
    echo  ================================================
    echo   [OK] Todos los tests pasaron correctamente.
    echo  ================================================
)

echo.
pause

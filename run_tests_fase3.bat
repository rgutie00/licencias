@echo off
REM ══════════════════════════════════════════════════════════
REM  run_tests_fase3.bat
REM  Ejecutar desde: C:\desarrollos\licencias\servidor\
REM ══════════════════════════════════════════════════════════

echo.
echo  ================================================
echo   SERVIDOR DE LICENCIAS - FASE 3 - TESTS
echo  ================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (echo [ERROR] Python no encontrado. & pause & exit /b 1)
echo  [OK] Python detectado.

echo.
echo  [1/2] Instalando dependencias...
pip install Django djangorestframework django-unfold psycopg2-binary dj-database-url pytest pytest-django pytest-cov -q
echo  [OK] Dependencias instaladas.

echo.
echo  [2/2] Ejecutando tests...
echo.
pytest test_api.py -v --tb=short -p no:warnings

echo.
if errorlevel 1 (
    echo  ================================================
    echo   [FALLO] Algunos tests fallaron.
    echo  ================================================
) else (
    echo  ================================================
    echo   [OK] Todos los tests de Fase 3 pasaron.
    echo        Servidor listo para desplegar.
    echo  ================================================
)
echo.
pause

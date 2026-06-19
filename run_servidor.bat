@echo off
REM ══════════════════════════════════════════════════════════
REM  run_servidor.bat
REM  Inicializa la DB y levanta el servidor de desarrollo.
REM  Ejecutar desde: C:\desarrollos\licencias\servidor\
REM ══════════════════════════════════════════════════════════

echo.
echo  ================================================
echo   SERVIDOR CENTRAL DE LICENCIAS
echo  ================================================
echo.

REM Instalar dependencias
echo  [1/4] Instalando dependencias...
pip install Django djangorestframework django-unfold dj-database-url -q
echo  [OK] Dependencias listas.

REM Migraciones
echo.
echo  [2/4] Aplicando migraciones...
python manage.py migrate --run-syncdb
echo  [OK] Base de datos lista.

REM Crear superusuario si no existe
echo.
echo  [3/4] Verificando superusuario...
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin','admin@licencias.com','admin123')" 2>nul
echo  [OK] Usuario admin listo (user: admin / pass: admin123)
echo  [AVISO] Cambia la clave en produccion!

REM Levantar servidor
echo.
echo  [4/4] Iniciando servidor en http://127.0.0.1:8000
echo        Panel Admin: http://127.0.0.1:8000/admin/
echo        API:         http://127.0.0.1:8000/api/v1/
echo.
python manage.py runserver 8000

pause

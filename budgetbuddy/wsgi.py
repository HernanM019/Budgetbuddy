"""
WSGI config for budgetbuddy project.

It exposes the WSGI callable as a module-level variable named ``application``.
Incluye verificación automática de migraciones y superusuario al iniciar Gunicorn,
garantizando que la base de datos (PostgreSQL o SQLite) tenga todas sus tablas listas
incluso tras reinicios de contenedor o cambios de variables en Render/Koyeb.
"""
import logging
import os

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budgetbuddy.settings')

application = get_wsgi_application()

try:
    call_command('migrate', interactive=False, verbosity=0)
    call_command('ensure_admin', verbosity=0)
except Exception as exc:
    logging.getLogger('budget.audit').warning(f"Aviso en auto-migrate de inicio WSGI: {exc}")

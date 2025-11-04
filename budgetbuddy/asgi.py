"""
ASGI config for budgetbuddy project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

"""
───────────────────────────────────────────────────────────────
ASGI configuration for BudgetBuddy
───────────────────────────────────────────────────────────────

ASGI = Asynchronous Server Gateway Interface
Es el PUENTE MODERNO del estándar WSGI.
Permite que Django maneje peticiones asíncronas, 
como WebSockets o tareas que no bloquean el flujo (async/await).

Django 3.0 en adelante soporta ASGI, lo cual lo hace apto
para servidores modernos como Daphne o Uvicorn.
───────────────────────────────────────────────────────────────
"""

import os
from django.core.asgi import get_asgi_application

# Misma configuración de entorno: indica dónde está settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budgetbuddy.settings')

# 'application' es el objeto ASGI, similar al de WSGI pero preparado para async.
application = get_asgi_application()


""""
Diferencias entre ambos

| Aspecto                | **WSGI** (antiguo)           | **ASGI** (nuevo)                                       |
| ---------------------- | ---------------------------- | ------------------------------------------------------ |
| Significa              | Web Server Gateway Interface | Asynchronous Server Gateway Interface                  |
| Naturaleza             | Sincrónica (bloqueante)      | Asíncrona (no bloqueante)                              |
| Ideal para             | Sitios web tradicionales     | Apps con WebSockets, notificaciones, chat, tiempo real |
| Ejemplos de servidores | Gunicorn, uWSGI              | Uvicorn, Daphne, Hypercorn                             |
| Django usa por defecto | WSGI                         | ASGI (disponible desde Django 3.0+)                    |
"""
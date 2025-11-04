"""
WSGI config for budgetbuddy project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

"""
───────────────────────────────────────────────────────────────
WSGI configuration for BudgetBuddy
───────────────────────────────────────────────────────────────

WSGI = Web Server Gateway Interface
Es el ESTANDAR CLASICO para que servidores web (como Gunicorn, uWSGI, o Apache mod_wsgi)
puedan comunicarse con frameworks Python como Django o Flask.

En términos simples:
Es un protocolo de comunicación entre servidores web y aplicaciones Python.
El proposito de esto es permitir que un servidor le diga a nuestro framework Django que se ha recibido una peticion HTTP
y que hay que devolver una respuesta.

El intermediario es una variable que se llama "APPLICATION" y esta ubicada en este archivo.
───────────────────────────────────────────────────────────────
"""

import os
from django.core.wsgi import get_wsgi_application

# Indica qué archivo de configuración (settings.py) usar.
# Igual que en manage.py, pero aquí se hace para los servidores web.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budgetbuddy.settings')

# 'application' es el objeto WSGI que el servidor necesita importar.
# Cuando se despliega la app, el servidor llamará:
#    from budgetbuddy.wsgi import application
# y usará este objeto para despachar cada request entrante.
application = get_wsgi_application()

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

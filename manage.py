#!/usr/bin/env python
"""
Django's command-line utility for administrative tasks.

───────────────────────────────────────────────────────────────
Rol de este archivo:
───────────────────────────────────────────────────────────────
Este script es el punto de entrada del proyecto Django desde la terminal.

Cada vez que ejecuto algo como:
    python manage.py runserver
o
    python manage.py migrate

este archivo:
    1. Configura la variable de entorno DJANGO_SETTINGS_MODULE
       (para que Django sepa dónde están las configuraciones del proyecto).
    2. Importa el motor interno de comandos de Django.
    3. Le pasa los argumentos que escribiste en la consola.
───────────────────────────────────────────────────────────────
"""

import os  # Permite interactuar con variables y rutas del sistema operativo.
import sys  # Permite acceder a los argumentos de la línea de comandos (sys.argv, etc.)


def main():
    """
    Función principal del script.

    ───────────────────────────────────────────────────────────────
    Qué hace:
    ───────────────────────────────────────────────────────────────
    1. Define la variable de entorno 'DJANGO_SETTINGS_MODULE'.
       Esto le indica a Django qué archivo de configuración usar
       (por ejemplo, budgetbuddy/settings.py).
    2. Intenta importar la utilidad principal de Django:
       'execute_from_command_line', que se encarga de ejecutar
       comandos administrativos.
    3. Si va bien, llama a esa función pasando los argumentos
       que el usuario escribió al ejecutar el script.
    ───────────────────────────────────────────────────────────────
    """

    # Establece una variable de entorno llamada DJANGO_SETTINGS_MODULE
    # Solo la define si aún no existe. Es clave para que Django sepa
    # dónde buscar el archivo settings.py de este proyecto.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budgetbuddy.settings')

    try:
        # Se importa la función que permite ejecutar comandos Django.
        # Esta función se encarga de interpretar lo que escribas en consola.
        from django.core.management import execute_from_command_line

    except ImportError as exc:
        # Si Django no está instalado en el entorno actual, se lanza un error
        # con un mensaje claro que te ayuda a diagnosticar el problema.
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Ejecuta el comando solicitado por el usuario.
    # Ejemplo:
    #   sys.argv = ['manage.py', 'runserver']
    #   Django ejecuta internamente el comando 'runserver' con las opciones dadas.
    execute_from_command_line(sys.argv)


# Este condicional evita que el script se ejecute automáticamente
# si es importado desde otro módulo.
# Solo se ejecutará si corrés directamente:  python manage.py <comando>
if __name__ == '__main__':
    main()

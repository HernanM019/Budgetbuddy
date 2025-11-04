"""
───────────────────────────────────────────────────────────────
BudgetBuddy - apps.py
───────────────────────────────────────────────────────────────

Este archivo define la *configuración de la app* dentro del ecosistema Django.

Cada aplicación (por ejemplo, 'budget', 'users', 'reports', etc.)
tiene su propia clase de configuración AppConfig, que le dice a Django:

  - Cómo se llama la app.
  - Qué campo usar como clave primaria por defecto.
  - (Opcional) Qué código ejecutar cuando la app se inicia.

Django lee esta clase automáticamente cuando la app está listada
en INSTALLED_APPS dentro de settings.py.
───────────────────────────────────────────────────────────────
"""

from django.apps import AppConfig


class BudgetConfig(AppConfig):
    """
    Clase de configuración de la app 'budget'.

    Django usa esta clase internamente para registrar la aplicación.
    """

    # Define el tipo de campo que Django usará como ID por defecto
    # cuando no se especifica ninguno en los modelos.
    default_auto_field = 'django.db.models.BigAutoField'

    # Nombre de la app (debe coincidir con el nombre de la carpeta del módulo)
    name = 'budget'

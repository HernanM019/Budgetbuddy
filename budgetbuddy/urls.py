"""
URL configuration for budgetbuddy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""


"""
───────────────────────────────────────────────────────────────
BudgetBuddy - URL Configuration
───────────────────────────────────────────────────────────────

Este archivo define el *enrutamiento principal* del proyecto Django.
Cada entrada de la lista `urlpatterns` conecta una URL con una vista 
(función o clase) que responde la petición.

Cuando el usuario visita una URL, Django sigue este orden:
    1. Busca el patrón que coincida en `urlpatterns`.
    2. Si lo encuentra, ejecuta la vista asociada.
    3. Devuelve la respuesta HTTP correspondiente (HTML, JSON, etc.).

───────────────────────────────────────────────────────────────
Documentación:
https://docs.djangoproject.com/en/5.2/topics/http/urls/
───────────────────────────────────────────────────────────────
"""

# ───────────────────────────────────────────────────────────────
# IMPORTACIONES NECESARIAS
# ───────────────────────────────────────────────────────────────
from django.contrib import admin
# 'admin' provee el panel administrativo estándar de Django (/admin o como se definas)

from django.urls import path, include
# 'path' | para definir rutas URL individuales
# 'include' | para conectar otras configuraciones de URLs (subrutas de apps, como 'budget/urls.py')

from django.contrib.auth import views as auth_views
# Importamos vistas genéricas de autenticación incluidas en Django:
# LoginView y LogoutView (listas para usar sin tener que crearlas manualmente)

from budget import views as budget_views
# Importamos vistas propias de nuestra app 'budget',
# por ejemplo la función 'register' (registro de usuario).



# ───────────────────────────────────────────────────────────────
# LISTA PRINCIPAL DE RUTAS DEL PROYECTO
# ───────────────────────────────────────────────────────────────
urlpatterns = [

    # Ruta al panel de administración de Django.
    # Por seguridad, renombramos '/admin/' a '/supervision-panel/' para ocultarlo. No tan eficiente pero sencillo.
    path('supervision-panel/', admin.site.urls),

    # Incluye todas las rutas definidas dentro del archivo 'budget/urls.py'.
    # Esto permite que la app 'budget' tenga su propio sistema de rutas.
    # Django buscará 'budget/urls.py' automáticamente.
    path('', include('budget.urls')),

    # Vista de inicio de sesión (login)
    # Usa la vista genérica de Django: LoginView
    # Le decimos qué template usar para renderizar el formulario.
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='budget/login.html'),
        name='login'
    ),

    # Vista de cierre de sesión (logout)
    # Usa LogoutView y redirige al usuario al login tras cerrar sesión.
    path(
        'logout/',
        auth_views.LogoutView.as_view(next_page='login'),
        name='logout'
    ),

    # Vista personalizada para el registro de nuevos usuarios.
    # Esta función 'register' está definida en 'budget/views.py'.
    path(
        'register/',
        budget_views.register,
        name='register'
    ),
]

"""""
COMO FUNCIONA:

El navegador pide una URL.
Django entra a este archivo (budgetbuddy/urls.py).

Busca coincidencia.
Si la URL empieza con algo como /login/, /register/ o /supervision-panel/, la maneja acá mismo.

Delegación.
Si no coincide con ninguna ruta explícita, Django pasa el control a budget/urls.py (por el include()).
Ahi están mis rutas internas de la aplicación (ej: /add_transaction/, /transactions/, /categories/, etc.).

La vista devuelve una respuesta.
→ Puede ser un HTML, JSON o redirección.
"""
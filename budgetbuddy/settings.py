"""
───────────────────────────────────────────────────────────────
Django settings for BudgetBuddy
───────────────────────────────────────────────────────────────

Este archivo define TODA la configuración del proyecto:
- Qué apps están instaladas.
- Cómo se conecta a la base de datos.
- Cómo maneja los idiomas, el timezone, los templates, los archivos estáticos, etc.

Cada vez que Django necesita leer algo del entorno (por ejemplo, la base de datos),
lo hace mirando este archivo.

Generado automáticamente por el comando:
    django-admin startproject budgetbuddy
───────────────────────────────────────────────────────────────
Documentación:
https://docs.djangoproject.com/en/5.2/topics/settings/
───────────────────────────────────────────────────────────────
"""

from pathlib import Path   # Biblioteca moderna para manipular rutas del sistema (más segura que os.path)
import os                  # Usada para operaciones de rutas y archivos (ej: unir carpetas)


# ───────────────────────────────────────────────────────────────
# BASE_DIR → Ruta base del proyecto
# ───────────────────────────────────────────────────────────────
# Ejemplo: si settings.py está en /home/hernan/budgetbuddy/budgetbuddy/,
# BASE_DIR termina siendo /home/hernan/budgetbuddy/
BASE_DIR = Path(__file__).resolve().parent.parent



# ───────────────────────────────────────────────────────────────
# CONFIGURACIONES DE SEGURIDAD Y DESARROLLO
# ───────────────────────────────────────────────────────────────

# Clave secreta para firmar cookies y tokens.
# Django la usa internamente para cifrar sesiones, contraseñas, etc.
# En producción, esta clave JAMÁS debe estar expuesta ni subir al repositorio.
SECRET_KEY = 'django-insecure-=df=dbz0@)n2+stpl68_@@6x!)nah%o9&2k!(ei!1420uvp2f2'

# Si DEBUG=True, Django muestra mensajes de error detallados en el navegador.
# En producción, siempre debe ser False (por seguridad).
DEBUG = True

# Lista de dominios/hosts que pueden acceder a tu aplicación.
# Vacío en desarrollo → acepta solo localhost (127.0.0.1).
# En producción deberías incluir dominios reales, ej:
# ALLOWED_HOSTS = ['budgetbuddy.com', 'www.budgetbuddy.com']
ALLOWED_HOSTS = []



# ───────────────────────────────────────────────────────────────
# APLICACIONES INSTALADAS
# ───────────────────────────────────────────────────────────────
# Django carga las apps listadas aquí en su sistema interno.
# Incluye tanto apps "core" (de Django) como las personalizadas del proyecto.
INSTALLED_APPS = [
    # Apps internas de Django
    'django.contrib.admin',            # Panel de administración (/admin)
    'django.contrib.auth',             # Sistema de autenticación de usuarios
    'django.contrib.contenttypes',     # Manejo de tipos de contenido (modelo-relación)
    'django.contrib.sessions',         # Manejo de sesiones (cookies del usuario)
    'django.contrib.messages',         # Sistema de mensajes flash (ej: "Transacción creada")
    'django.contrib.staticfiles',      # Manejo de archivos estáticos (CSS, JS, imágenes)

    # ─── Apps propias del proyecto ───
    'budget',  # Nuestra app interna donde vive la lógica de BudgetBuddy
]



# ───────────────────────────────────────────────────────────────
# MIDDLEWARE
# ───────────────────────────────────────────────────────────────
# Los middleware son funciones que se ejecutan entre la request del usuario
# y la respuesta de Django. Cada capa agrega o modifica información.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',            # Seguridad básica (headers, HTTPS)
    'django.contrib.sessions.middleware.SessionMiddleware',     # Habilita las sesiones
    'django.middleware.common.CommonMiddleware',                # Cabeceras y normalización de requests
    'django.middleware.csrf.CsrfViewMiddleware',                # Protección contra ataques CSRF en formularios
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Asocia usuario a request
    'django.contrib.messages.middleware.MessageMiddleware',     # Habilita el sistema de mensajes flash
    'django.middleware.clickjacking.XFrameOptionsMiddleware',   # Previene ataques clickjacking
]



# ───────────────────────────────────────────────────────────────
# ARCHIVO PRINCIPAL DE URLS
# ───────────────────────────────────────────────────────────────
# Indica el módulo donde está el "mapa de rutas" del proyecto.
# Django irá a budgetbuddy/urls.py


"""
INSTALLED_APPS dice qué “módulos funcionales” tiene tu proyecto.

MIDDLEWARE son capas de seguridad, autenticación, sesiones, etc.

DATABASES define el motor y la ubicación de la base de datos.

STATICFILES_DIRS es donde Django busca tus CSS y JS.

LOGIN_URL / REDIRECT_URLS controlan la navegación post-login/logout.

Nunca se sube la SECRET_KEY real a GitHub.
En producción se guarda en variables de entorno, no en el código.
"""
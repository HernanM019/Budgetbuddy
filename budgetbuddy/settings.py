"""
Django settings for budgetbuddy project.
Configurado con soporte multi-entorno (DATABASE_URL para Neon/Render/Koyeb, POSTGRES_DB y SQLite),
hashing Argon2 / BCrypt, DRF + JWT + OpenAPI, Celery + Redis (con fallback eager automático),
WhiteNoise y Logging de Auditoría de Seguridad.
"""
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import os

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Manejo seguro de secretos mediante variables de entorno con fallback solo para desarrollo local
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-=df=dbz0@)n2+stpl68_@@6x!)nah%o9&2k!(ei!1420uvp2f2',
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0,testserver,.onrender.com,.koyeb.app').split(',')
    if host.strip()
]

# Detección automática de dominio asignado por Render.com o Koyeb
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

KOYEB_PUBLIC_DOMAIN = os.environ.get('KOYEB_PUBLIC_DOMAIN')
if KOYEB_PUBLIC_DOMAIN and KOYEB_PUBLIC_DOMAIN not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(KOYEB_PUBLIC_DOMAIN)

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        'DJANGO_CSRF_TRUSTED_ORIGINS',
        'http://localhost:8000,http://127.0.0.1:8000,https://*.onrender.com,https://*.koyeb.app',
    ).split(',')
    if origin.strip()
]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")
if KOYEB_PUBLIC_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f"https://{KOYEB_PUBLIC_DOMAIN}")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    # Local apps
    'budget',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'budgetbuddy.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'budgetbuddy.wsgi.application'


def _parse_database_url(db_url: str) -> dict:
    """
    Convierte una cadena DATABASE_URL (ej. de Neon.tech, Render o Supabase)
    en un diccionario de configuración DATABASES de Django sin dependencias externas.
    """
    parsed = urlparse(db_url)
    query_opts = parse_qs(parsed.query)
    options = {}
    if 'sslmode' in query_opts:
        options['sslmode'] = query_opts['sslmode'][0]

    config = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': parsed.path.lstrip('/'),
        'USER': unquote(parsed.username or ''),
        'PASSWORD': unquote(parsed.password or ''),
        'HOST': parsed.hostname or 'localhost',
        'PORT': str(parsed.port or 5432),
        'CONN_MAX_AGE': 600,
    }
    if options:
        config['OPTIONS'] = options
    return config


# Base de datos:
# 1. Prioriza DATABASE_URL (Neon.tech / Render / Koyeb)
# 2. Luego variables individuales POSTGRES_DB (Docker Compose / GitHub Actions)
# 3. Por defecto SQLite local para desarrollo rápido
if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': _parse_database_url(os.environ['DATABASE_URL'])
    }
elif os.environ.get('POSTGRES_DB'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'budgetbuddy'),
            'USER': os.environ.get('POSTGRES_USER', 'budgetbuddy_user'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'budgetbuddy_pass'),
            'HOST': os.environ.get('POSTGRES_HOST', 'db'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Caché en memoria para Rate Limiting (o Redis en producción)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'budgetbuddy-security-cache',
    }
}

# Configuración de Celery + Redis
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'max_retries': 1,
    'interval_start': 0,
    'interval_step': 0.1,
    'interval_max': 0.2,
}
# Si no se define CELERY_BROKER_URL en el entorno, ejecuta las tareas en modo eager (inmediato)
_default_eager = 'False' if os.environ.get('CELERY_BROKER_URL') else 'True'
CELERY_TASK_ALWAYS_EAGER = os.environ.get('CELERY_TASK_ALWAYS_EAGER', _default_eager).lower() in ('true', '1', 'yes')
CELERY_TASK_EAGER_PROPAGATES = True

# Django REST Framework + JWT + OpenAPI (drf-spectacular)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'BudgetBuddy Financial REST API',
    'DESCRIPTION': 'API REST Multi-Tenant para gestión de cuentas, transacciones, presupuestos y soporte en BudgetBuddy.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Hashing seguro de contraseñas con Argon2id como algoritmo primario y BCrypt como secundario
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Seguridad de Sesiones, Cookies y Cabeceras HTTP detrás de Proxy HTTPS (Render / Koyeb)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False  # Permite lectura por fetch AJAX en eliminación con token CSRF
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', 'True').lower() == 'true'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Configuración de Correo Electrónico (Alertas de Tickets a Admins y Recuperación de Contraseña)
EMAIL_BACKEND = os.environ.get(
    'DJANGO_EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend',
)
DEFAULT_FROM_EMAIL = os.environ.get('DJANGO_DEFAULT_FROM_EMAIL', 'alertas@budgetbuddy.local')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# Logging Estructurado de Auditoría de Seguridad y Operaciones
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'structured': {
            'format': '[{asctime}] [{levelname}] [{name}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'structured',
        },
        'security_file': {
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'security_audit.log',
            'formatter': 'structured',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'budget.security': {
            'handlers': ['console', 'security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'budget.audit': {
            'handlers': ['console', 'security_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Internacionalización
LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Archivos Estáticos (WhiteNoise para Producción / Staging)
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'budget', 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
os.makedirs(STATIC_ROOT, exist_ok=True)
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

# Redirecciones de Autenticación
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'landing_page'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

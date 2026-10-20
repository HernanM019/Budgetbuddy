# ☁️ Guía Completa de Despliegue Gratuito ($0) — BudgetBuddy Staging / Tech Demo

Esta guía paso a paso te permitirá publicar **BudgetBuddy** en internet de forma **100% gratuita**, con base de datos **PostgreSQL 16 persistente**, certificado **HTTPS** automático y diseño **Mobile-Responsive** accesible desde cualquier celular o computadora del mundo.

---

## 🏆 Arquitectura del Hosting Gratuito Recomendado

Para evitar el límite de 30 días de la base de datos gratuita de Render, combinamos los dos mejores servicios gratuitos actuales:
1. **Base de Datos PostgreSQL 16**: **[Neon.tech](https://neon.tech/)** (Plan *Free Tier* permanente, sin tarjeta de crédito, 0.5 GB de almacenamiento persistente).
2. **Servidor Web Python / Django**: **[Render.com](https://render.com/)** (Plan *Free Web Service*, conectado automáticamente a tu repositorio de GitHub).

---

## Paso 1: Subir los últimos cambios a tu repositorio de GitHub

En tu terminal de PyCharm / PowerShell, dentro de `C:\Users\herna\PycharmProjects\Budgetbuddy`:

```powershell
git add .
git commit -m "feat: complete v1.1 rework with multi-tenant core, DRF, Celery, CSV ETL, support center and Render config"
git push origin main
```

*(Al hacer `git push`, GitHub Actions ejecutará automáticamente el pipeline `.github/workflows/ci.yml` validando los 22 tests de seguridad).*

---

## Paso 2: Crear la Base de Datos PostgreSQL Gratis en Neon.tech (2 minutos)

1. Ingresa a **[https://neon.tech/](https://neon.tech/)** e inicia sesión con tu cuenta de **GitHub**.
2. Haz clic en **"Create Project"**:
   - **Project name**: `budgetbuddy-db`
   - **Region**: Elige `US East (Ohio)` o `US East (N. Virginia)` (la misma región que usarás en Render).
3. Una vez creado, en el **Dashboard de Neon** verás un cuadro llamado **Connection string**.
4. Copia la URL completa (tiene este formato):
   ```text
   postgresql://neondb_owner:AbCdEf123456@ep-cool-name-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   *(Guárdala para pegarla en el Paso 3 como `DATABASE_URL`).*

---

## Paso 3: Publicar la Aplicación Web Gratis en Render.com (3 minutos)

El repositorio ya incluye el archivo **[render.yaml](./render.yaml)** y el comando automático `python manage.py ensure_admin` (que crea tu cuenta de administrador sin necesidad de consola SSH paga).

1. Ingresa a **[https://render.com/](https://render.com/)** e inicia sesión con tu cuenta de **GitHub**.
2. Haz clic en el botón **"New +"** (arriba a la derecha) → selecciona **"Web Service"**.
3. Conecta tu repositorio **`Budgetbuddy`**.
4. Configura los siguientes campos:
   - **Name**: `budgetbuddy-demo` (tu URL será `https://budgetbuddy-demo.onrender.com`)
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate && python manage.py ensure_admin
     ```
   - **Start Command**:
     ```bash
     gunicorn budgetbuddy.wsgi:application --bind 0.0.0.0:$PORT --workers 2
     ```
   - **Instance Type**: Selecciona **Free ($0/month)**.
5. Baja hasta la sección **Environment Variables** y agrega las siguientes variables:

| Variable (`Key`) | Valor (`Value`) | Propósito |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://neondb_owner:...@ep-...neon.tech/neondb?sslmode=require` | Conecta Django con tu PostgreSQL gratuito de Neon.tech. |
| `DJANGO_SECRET_KEY` | *(Cualquier texto aleatorio largo, ej. `bb-prod-98f7a6s5d4f3g2h1j0k9l8m7n6b5v4c3x2z1`)* | Firma criptográfica de sesiones y tokens JWT. |
| `DJANGO_DEBUG` | `False` | Activa modo seguro de producción y HSTS/Cookies seguras. |
| `CELERY_TASK_ALWAYS_EAGER` | `True` | Ejecuta las alertas de tickets y presupuestos en el mismo contenedor sin requerir pagar Redis extra. |
| `DJANGO_SUPERUSER_USERNAME` | `Hernan` | Crea automáticamente tu usuario Admin al desplegar. |
| `DJANGO_SUPERUSER_EMAIL` | *(Tu correo real, ej. `tu_correo@gmail.com`)* | Recibirá los correos automáticos de nuevos tickets/sugerencias. |
| `DJANGO_SUPERUSER_PASSWORD` | *(Tu contraseña segura de administrador)* | Clave de acceso para tu usuario Admin (se cifrará con Argon2id). |

6. Haz clic en **"Create Web Service"**. En unos 2–3 minutos verás el estado **`Live`** y podrás compartir el link `https://budgetbuddy-demo.onrender.com` con cualquier amigo o reclutador.

---

## Paso 4 (Opcional): Activar envío de Emails reales con Gmail SMTP

Si quieres que cuando un amigo deje una sugerencia o ticket en la demo pública te llegue un correo real a tu bandeja de Gmail:

1. En tu cuenta de Google, ve a **Seguridad → Verificación en 2 pasos → Contraseñas de aplicaciones (App Passwords)** y genera una clave de 16 letras para `"BudgetBuddy"`.
2. En **Render → Environment Variables**, agrega:
   - `DJANGO_EMAIL_BACKEND` = `django.core.mail.backends.smtp.EmailBackend`
   - `EMAIL_HOST` = `smtp.gmail.com`
   - `EMAIL_PORT` = `587`
   - `EMAIL_USE_TLS` = `True`
   - `EMAIL_HOST_USER` = `tu_correo@gmail.com`
   - `EMAIL_HOST_PASSWORD` = `xxxx xxxx xxxx xxxx` *(tu contraseña de aplicación de 16 letras)*
   - `DJANGO_DEFAULT_FROM_EMAIL` = `tu_correo@gmail.com`
3. Cada nuevo ticket llegará con el asunto:
   - `[BudgetBuddy | 💡 Sugerencia / Nueva Idea] Ticket #1: ...`
   - `[BudgetBuddy | 🐛 Falla o Error Técnico] Ticket #2: ...`
   - `[BudgetBuddy | 🔐 Problema de Acceso / Contraseña] Ticket #3: ...`
   Listo para filtrar por carpetas en tu correo.

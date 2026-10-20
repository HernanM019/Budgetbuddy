# 💰 BudgetBuddy — Plataforma Multi-Usuario de Finanzas Personales

**BudgetBuddy** es una aplicación web completa de finanzas personales construida con **Python 3.12 y Django 5.2**, diseñada bajo una **Arquitectura en Capas Limpias (Presentación/API, Servicios de Dominio y Repositorios ORM)** con **aislamiento multi-usuario estricto (Data Segregation)**.

---

## 🌟 Características Principales

- 🎨 **Landing Page Moderna y Diseño 100% Mobile-Responsive**:
  - Interfaz adaptable a celulares, tablets y escritorio con tipografía *Plus Jakarta Sans*, navbar *glassmorphism* y redirección automática al Dashboard si existe sesión activa.
- 🔐 **Seguridad de Nivel Empresarial y Área Personal (`/profile/`)**:
  - Hashing de contraseñas con **Argon2id** (primario) y **BCrypt** (secundario).
  - **Rate Limiting** contra fuerza bruta en `/login/` (bloqueo HTTP 429 tras 5 intentos fallidos).
  - **Área Personal (`/profile/`)**: Edición de nombre, apellido, correo electrónico único y cambio de contraseña manteniendo la sesión activa (`update_session_auth_hash`).
  - Bitácora estructurada de auditoría de seguridad en `logs/security_audit.log`.
- 🛡️ **Aislamiento Multi-Usuario en 4 Niveles (Zero IDOR)**:
  - Cada usuario opera en un espacio privado: sus cuentas, categorías, transacciones, presupuestos y tickets están aislados en Vistas, Formularios/Serializers, Servicios y Repositorios.
- 🏦 **Módulo Financiero Central**:
  - **Cuentas (`Account`)**: Efectivo, Cuenta Bancaria, Billetera Virtual, Ahorros y Crédito con cálculo de patrimonio neto consolidado.
  - **Movimientos y Transferencias (`/transactions/`, `/transfer/`)**: Ingresos, egresos y transferencias atómicas (`@transaction.atomic`) entre cuentas.
  - **Exportación e Importación CSV (ETL Práctico)**: Descarga compatible con Microsoft Excel (UTF-8 BOM) e importación masiva desde archivos `.csv`.
  - **Presupuestos Mensuales (`Budget`) + Alertas Celery**: Barras de progreso en tiempo real y envío automático de alertas por email cuando el gasto supera el **80%** o **100%**.
- 💡 **Centro de Sugerencias y Soporte (`/support/` y `/support/manage/`)**:
  - Accesible desde la Landing Page (sin login) y desde dentro de la aplicación.
  - **Notificación automática por email a Administradores (`is_staff`/`is_superuser`)**: Incluye el motivo seleccionado en el `Subject` (`[BudgetBuddy | 💡 Sugerencia / Nueva Idea]`, etc.) para filtrado automático por carpetas de correo.
  - **Buzón Admin (`/support/manage/`)**: Panel para moderar ideas del roadmap y responder tickets de usuarios.
- 🌐 **API RESTful con DRF + JWT + Swagger UI (`/api/v1/docs/`)**:
  - Endpoints REST completos protegidos con JWT (`SimpleJWT`) y documentados con OpenAPI 3 (`drf-spectacular`).

---

## 📚 Documentación Técnica del Proyecto

| Documento | Contenido |
| :--- | :--- |
| 🏛️ **[ARCHITECTURE.md](./ARCHITECTURE.md)** | Arquitectura en 3 capas, Diagrama de Casos de Uso UML, Diagramas de Secuencia (Auth, Argon2, Celery, Soporte) y Modelo Entidad-Relación (ERD) en Mermaid. |
| ☁️ **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** | Instructivo paso a paso para publicar el sitio **100% gratis ($0)** en **Render.com + Neon.tech PostgreSQL** y configurar correo SMTP con Gmail. |
| 📝 **[CHANGELOG.md](./CHANGELOG.md)** | Historial detallado de versiones y evolución del proyecto desde `v0.1` hasta `v1.1.0`. |

---

## 🛠️ Instructivo de Instalación y Uso Local

### 1. Clonar e instalar dependencias
```powershell
cd "C:\Users\herna\PycharmProjects\Budgetbuddy"
.\.venv\Scripts\pip.exe install -r requirements.txt
```

### 2. Aplicar migraciones y crear superusuario (opcional)
```powershell
.\.venv\Scripts\python.exe manage.py migrate
# Opcional: crear/actualizar superusuario mediante variables de entorno
$env:DJANGO_SUPERUSER_USERNAME="Hernan"
$env:DJANGO_SUPERUSER_EMAIL="tu@email.com"
$env:DJANGO_SUPERUSER_PASSWORD="TuPasswordSeguro123!"
.\.venv\Scripts\python.exe manage.py ensure_admin
```

### 3. Iniciar el servidor de desarrollo
```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```
- **Aplicación Web**: `http://127.0.0.1:8000/`
- **Documentación Interactiva API (Swagger UI)**: `http://127.0.0.1:8000/api/v1/docs/`
- **Buzón de Soporte y Sugerencias (Admin)**: `http://127.0.0.1:8000/support/manage/`

### 4. Ejecutar con Docker Compose (Django + PostgreSQL 16 + Redis 7 + Celery Worker)
```bash
docker compose up --build
```

### 5. Ejecutar la Suite de Pruebas Automatizadas (22 Tests)
```powershell
.\.venv\Scripts\python.exe manage.py test -v 2
```

---

## 🧭 Estado del Roadmap v3.0

| Stage | Módulo / Hito | Estado | Detalle |
| :--- | :--- | :--- | :--- |
| **0** | 🔧 **Multi-Tenant Core & Landing Page** | ✅ **Completado** | Cuentas, Categorías, Transacciones, Transferencias y Presupuestos en capas limpias. |
| **1** | 🔒 **Seguridad Argon2, Área Personal y Centro de Soporte** | ✅ **Completado** | Rate Limiting, `/profile/`, `/support/`, `/support/manage/` y alertas email a admins. |
| **2** | 🔄 **ETL Práctico (CSV Export / Import)** | ✅ **Completado** | Exportación Excel UTF-8 BOM e importación masiva validada. |
| **3** | ⚙️ **Celery + Redis Async Tasks** | ✅ **Completado** | Alertas por email al superar 80%/100% de presupuesto y avisos de tickets. |
| **4** | 🌐 **Django REST Framework + JWT + Swagger** | ✅ **Completado** | API REST completa en `/api/v1/` y documentación interactiva en `/api/v1/docs/`. |
| **5** | 📊 **Observabilidad & Security Audit Logging** | ✅ **Completado** | Bitácora estructurada en `logs/security_audit.log`. |
| **6** | 🔄 **CI/CD (GitHub Actions) & Docker** | ✅ **Completado** | Pipeline `.github/workflows/ci.yml` con PostgreSQL 16 + Redis 7 + Docker build. |
| **7** | ☁️ **Public Cloud Staging Ready** | ✅ **Listo para publicar** | Configurado con `render.yaml`, `build.sh`, `DATABASE_URL` (Neon.tech) y `WhiteNoise`. |

## [2025-10-17] BudgetBuddy v0.1
- Added Transaction model and admin integration
- Implemented transaction list and balance summary view
- Created form for adding transactions via frontend
- Base project fully functional with SQLite

## [2025-10-17] BudgetBuddy v0.2
- Integrated Bootstrap 5 for responsive UI
- Added navigation bar and consistent layout
- Implemented Django template inheritance with base.html
- Updated all views to use shared design

## [2025-10-17] BudgetBuddy v0.3
- Integrated SweetAlert2 for modern confirmation popups
- Enabled dynamic (AJAX-based) deletion of transactions without reloading the page
- Added smooth fade-out animation for deleted table rows

## [2025-10-18] BudgetBuddy v0.4
- Added transaction editing feature (Update) to complete CRUD operations

## [2025-10-18] BudgetBuddy v0.5  
- Implementado sistema completo de autenticación de usuarios (login, logout y registro)
- Asociación de registros financieros a cada usuario

## [2025-10-26] BudgetBuddy v0.5.1
- Added full CRUD for user-specific Categories (linked to authenticated users)

## [2026-10-20] BudgetBuddy v1.0.0 — Complete Architectural Rework & Multi-Tenant Suite
- **Arquitectura en Capas Limpias**: Separación en Capa de Presentación (`views.py`, `forms.py`), Capa de Servicios (`services.py`) y Capa de Repositorio (`repositories.py`).
- **Landing Page de Conversión (`/`)**: Nueva portada pública con redirección automática al Dashboard para usuarios autenticados.
- **Seguridad y Aislamiento Multi-Usuario (IDOR Fix)**:
  - Corregida vulnerabilidad IDOR en eliminación/edición de transacciones y agregados decoradores `@login_required`.
  - Hashing de contraseñas actualizado a **Argon2id** y **BCrypt**.
  - **Rate Limiting** contra fuerza bruta en `/login/` (HTTP 429 tras 5 intentos fallidos).
- **Nuevos Módulos Financieros**: Cuentas (`Account`), Transferencias atómicas (`/transfer/`), Presupuestos Mensuales (`Budget`) y Balances Históricos.

## [2026-10-20] BudgetBuddy v1.1.0 — Profile, Support Center, DRF API, Celery, CSV ETL & Cloud Staging
- **Área Personal (`/profile/`)**: Actualización de nombre, apellido, correo único y cambio seguro de contraseña manteniendo la sesión activa (`update_session_auth_hash`).
- **Centro de Sugerencias y Soporte (`/support/` y `/support/manage/`)**:
  - Envío de sugerencias de producto y reportes técnicos tanto desde la Landing Page como para usuarios logueados.
  - **Alertas automáticas por email a Administradores (`is_staff`/`is_superuser`)** con el motivo seleccionado en el `Subject` para filtrado por carpetas.
  - Panel de moderación y respuesta para administradores en `/support/manage/`.
- **ETL Práctico CSV (`/transactions/export/csv/` y `/transactions/import/csv/`)**: Exportación compatible con Excel e importación masiva de movimientos.
- **Celery + Redis (`budget/tasks.py`)**: Envío asíncrono de alertas cuando un presupuesto mensual alcanza el 80% o 100%, con fallback síncrono automático.
- **API RESTful (DRF + SimpleJWT + Swagger `/api/v1/docs/`)**: ViewSets y Serializers aislados por usuario.
- **CI/CD & Cloud Staging**: Pipeline `.github/workflows/ci.yml`, `render.yaml`, `build.sh`, comando `ensure_admin`, soporte `DATABASE_URL` (Neon.tech), `WhiteNoise` y diseño 100% Mobile-Responsive.

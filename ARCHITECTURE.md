# 🏗️ Arquitectura de Software, Casos de Uso y Modelo de Datos — BudgetBuddy v1.1

Este documento constituye la referencia técnica oficial de **BudgetBuddy**. Describe su arquitectura en capas limpias, los diagramas de casos de uso completos, los flujos de autenticación y notificaciones asíncronas, el modelo entidad-relación (ERD) y la estrategia de aislamiento multi-usuario (*Data Segregation*).

---

## 1. Arquitectura de Software en Capas Limpias (Layered Architecture)

El sistema implementa una separación estricta en **3 capas** dentro de la aplicación `budget/`, complementada con procesamiento asíncrono (**Celery + Redis**) y una **API RESTful (DRF + JWT + OpenAPI)**:

1. **Capa de Presentación y API (`views.py`, `api_views.py`, `forms.py`, `serializers.py`, `urls.py`, `api_urls.py`)**:
   - Gestiona peticiones HTTP SSR (Django Templates + Bootstrap 5 Mobile-Responsive) y endpoints REST (`/api/v1/`).
   - Aplica control de acceso (`@login_required`, `IsAuthenticated`), tokens JWT (`SimpleJWT`) y validación de entrada.
2. **Capa de Servicios / Lógica de Negocio (`services.py` y `tasks.py`)**:
   - Contiene la lógica de dominio desacoplada:
     - `OnboardingService`: Aprovisionamiento atómico de cuenta principal y 7 categorías iniciales al registrarse.
     - `TransactionService`: Validación de pertenencia multi-tenant (`validate_ownership`), registro de ingresos/egresos y transferencias atómicas entre cuentas (`@transaction.atomic`).
     - `BudgetService`: Cálculo de ejecución mensual y umbrales de alerta (`Saludable < 80%`, `En alerta 80-99%`, `Excedido >= 100%`).
     - `CSVDataService`: Exportación compatible con Excel (UTF-8 BOM) e importación masiva de transacciones desde CSV.
     - `SupportTicketService`: Creación de sugerencias/tickets y despacho de alertas por correo a administradores.
     - `AuthRateLimitService`: Bloqueo temporal contra fuerza bruta en login (máx. 5 intentos fallidos / 5 min) y bitácora en `budget.security`.
     - `tasks.py` (Celery): Envío asíncrono de correos de soporte y alertas de presupuesto con fallback síncrono automático (`dispatch_task_safely`).
3. **Capa de Persistencia / Repositorio (`repositories.py`)**:
   - Centraliza todas las consultas ORM (`AccountRepository`, `CategoryRepository`, `TransactionRepository`, `BudgetRepository`, `SupportTicketRepository`).
   - Exige `user: User` en cada método de datos privados y optimiza lecturas con `select_related` y agregaciones SQL (`Sum`, `Coalesce`, `TruncMonth`).

```mermaid
flowchart TD
    subgraph Presentation["1. Capa de Presentación Web & REST API"]
        LP["Landing Page Pública (/)"]
        Views["Vistas Web SSR (views.py + forms.py)"]
        DRF["API REST v1 (api_views.py + serializers.py + JWT)"]
        Swagger["OpenAPI / Swagger UI (/api/v1/docs/)"]
    end

    subgraph ServiceLayer["2. Capa de Servicios de Dominio & Tareas Asíncronas"]
        AuthRL["AuthRateLimitService (Anti Brute-Force & Audit Log)"]
        Onboard["OnboardingService (Provisioning Inicial)"]
        TxSvc["TransactionService (CRUD & Transferencias Atómicas)"]
        CSVSvc["CSVDataService (Export / Import CSV ETL)"]
        BudgetSvc["BudgetService (Umbrales 80% / 100%)"]
        DashSvc["DashboardService (Consolidación de KPIs)"]
        SupSvc["SupportTicketService (Sugerencias y Soporte)"]
        CeleryTasks["Celery Tasks (tasks.py: Emails Admin & Alertas Budget)"]
    end

    subgraph RepositoryLayer["3. Capa de Persistencia / Repositorios (repositories.py)"]
        AccRepo["AccountRepository (user=request.user)"]
        CatRepo["CategoryRepository (user=request.user)"]
        TxRepo["TransactionRepository (select_related + SQL Sum)"]
        BudRepo["BudgetRepository (user=request.user)"]
        SupRepo["SupportTicketRepository (user / staff filter)"]
    end

    subgraph Infra["Persistencia & Mensajería"]
        DB[("PostgreSQL 16 / SQLite")]
        Redis[("Redis Broker / Eager Fallback")]
        SMTP["Servidor SMTP / Console Email"]
    end

    LP --> Views
    LP --> SupSvc
    Views --> AuthRL
    Views --> Onboard
    Views --> TxSvc
    Views --> CSVSvc
    Views --> BudgetSvc
    Views --> DashSvc
    Views --> SupSvc
    DRF --> TxSvc
    DRF --> SupSvc
    DRF --> AccRepo
    DRF --> CatRepo
    DRF --> TxRepo
    DRF --> BudRepo
    Swagger --> DRF

    TxSvc --> CeleryTasks
    SupSvc --> CeleryTasks
    CeleryTasks --> Redis
    CeleryTasks --> SMTP

    Onboard --> AccRepo
    Onboard --> CatRepo
    TxSvc --> TxRepo
    TxSvc --> AccRepo
    CSVSvc --> TxRepo
    CSVSvc --> CatRepo
    BudgetSvc --> BudRepo
    BudgetSvc --> TxRepo
    DashSvc --> AccRepo
    DashSvc --> TxRepo
    DashSvc --> BudgetSvc
    SupSvc --> SupRepo

    AccRepo --> DB
    CatRepo --> DB
    TxRepo --> DB
    BudRepo --> DB
    SupRepo --> DB
```

---

## 2. Diagrama de Casos de Uso Completo (UML en Mermaid)

```mermaid
flowchart LR
    Anon["👤 Visitante No Autenticado"]
    AuthUser["🔐 Usuario Autenticado"]
    Admin["🛡️ Administrador (Staff / Superuser)"]

    subgraph PublicScope["1. Espacio Público y Conversión"]
        UC_Landing["Explorar Landing Page Mobile-Responsive (/)"]
        UC_Register["Registrarse con Onboarding Automático (/register/)"]
        UC_Login["Iniciar Sesión con Protección Brute-Force (/login/)"]
        UC_Reset["Recuperar Contraseña por Email (/password-reset/)"]
        UC_PubSupport["Enviar Reporte de Acceso o Sugerencia sin Login (/support/)"]
    end

    subgraph PrivateScope["2. Espacio Financiero y Personal Aislado (Multi-Tenant)"]
        UC_Dash["Visualizar Dashboard, Patrimonio y Balance Histórico (/dashboard/)"]
        UC_Profile["Gestionar Área Personal: Email, Nombre y Cambio de Contraseña (/profile/)"]
        UC_Accounts["Administrar Cuentas Financieras Multi-Moneda (/accounts/)"]
        UC_Tx["Registrar, Filtrar, Editar y Eliminar Ingresos/Egresos (/transactions/)"]
        UC_Transfer["Ejecutar Transferencias Atómicas entre Cuentas (/transfer/)"]
        UC_CSV["Exportar Movimientos a Excel CSV e Importar Lotes CSV"]
        UC_Cat["Personalizar Categorías con Color y Tipo (/categories/)"]
        UC_Budget["Configurar Presupuestos Mensuales y Recibir Alertas Email 80%/100% (/budgets/)"]
        UC_UserSupport["Enviar Sugerencias/Tickets y Consultar Respuestas del Admin (/support/)"]
        UC_API["Consumir API REST con JWT y Explorar Swagger (/api/v1/docs/)"]
        UC_Logout["Cerrar Sesión de Forma Segura (/logout/)"]
    end

    subgraph AdminScope["3. Gestión y Moderación del Sitio"]
        UC_AdminInbox["Revisar Ideas/Sugerencias, Filtrar Tickets y Responder (/support/manage/)"]
        UC_EmailAlert["Recibir Alertas Email Automáticas con Etiqueta de Motivo en Subject"]
        UC_DjangoAdmin["Auditar Entidades en Panel de Supervisión (/supervision-panel/)"]
    end

    Anon --> UC_Landing
    Anon --> UC_Register
    Anon --> UC_Login
    Anon --> UC_Reset
    Anon --> UC_PubSupport

    AuthUser --> UC_Dash
    AuthUser --> UC_Profile
    AuthUser --> UC_Accounts
    AuthUser --> UC_Tx
    AuthUser --> UC_Transfer
    AuthUser --> UC_CSV
    AuthUser --> UC_Cat
    AuthUser --> UC_Budget
    AuthUser --> UC_UserSupport
    AuthUser --> UC_API
    AuthUser --> UC_Logout

    Admin --> UC_AdminInbox
    Admin --> UC_EmailAlert
    Admin --> UC_DjangoAdmin
```

---

## 3. Flujos de Secuencia Principales

### 3.1 Autenticación, Hashing Argon2id, Rate Limiting y Cambio de Contraseña

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant V as Views (login_view / profile_view)
    participant RL as AuthRateLimitService
    participant H as Argon2PasswordHasher
    participant Log as Security Logger (security_audit.log)
    participant DB as PostgreSQL / SQLite

    Note over U,DB: Inicio de Sesión con Protección Anti Fuerza Bruta
    U->>V: POST /login/ (username, password)
    V->>RL: is_locked(ip, username)
    alt Bloqueado (>= 5 intentos fallidos en 5 min)
        RL->>Log: WARNING Bloqueo Rate-Limit activo
        V-->>U: HTTP 429 Too Many Requests
    else Permitido
        V->>H: Verificar contraseña contra hash Argon2id
        alt Credenciales Inválidas
            V->>RL: record_failure(ip, username)
            RL->>Log: INFO Fallo de autenticación #N
            V-->>U: 200 OK (Mensaje de error)
        else Credenciales Válidas
            V->>RL: reset(ip, username)
            V-->>U: Cookie sessionid (HttpOnly, SameSite=Lax) + 302 -> /dashboard/
        end
    end

    Note over U,DB: Cambio de Contraseña en Área Personal (/profile/)
    U->>V: POST /profile/ (action=change_password)
    V->>H: Valida clave actual y genera nuevo hash Argon2id
    H->>DB: UPDATE auth_user SET password='argon2$...'
    V->>V: update_session_auth_hash(request, user)
    V-->>U: 302 Redirect -> /profile/ (Sesión permanece activa)
```

### 3.2 Creación de Ticket/Sugerencia y Alerta Automática por Email a Administradores

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario o Visitante
    participant V as support_center (views.py)
    participant S as SupportTicketService
    participant T as Celery Task (send_admin_ticket_notification_task)
    participant R as SupportTicketRepository
    participant M as Servidor Email / SMTP

    U->>V: POST /support/ (ticket_type, subject, message, contact_email)
    V->>S: create_ticket(ticket, user)
    S->>R: INSERT budget_supportticket
    S->>T: dispatch_task_safely(send_admin_ticket_notification_task, ticket.id)
    T->>R: get_admin_recipient_emails() (is_staff=True OR is_superuser=True con email)
    R-->>T: Lista de correos de administradores activos
    T->>M: send_mail(Subject="[BudgetBuddy | <Motivo>] Ticket #ID: <Asunto>", Body=Detalle completo)
    V-->>U: 302 Redirect -> /support/ (Confirmación visual)
```

---

## 4. Modelo Entidad-Relación Normalizado (ERD)

```mermaid
erDiagram
    USER ||--o{ ACCOUNT : "posee (CASCADE)"
    USER ||--o{ CATEGORY : "define (CASCADE)"
    USER ||--o{ TRANSACTION : "registra (CASCADE)"
    USER ||--o{ BUDGET : "planifica (CASCADE)"
    USER ||--o{ SUPPORT_TICKET : "envía (SET_NULL)"

    ACCOUNT ||--o{ TRANSACTION : "cuenta origen (CASCADE)"
    ACCOUNT ||--o{ TRANSACTION : "cuenta destino (SET_NULL)"
    CATEGORY ||--o{ TRANSACTION : "clasifica (SET_NULL)"
    CATEGORY ||--o{ BUDGET : "limita (CASCADE)"

    USER {
        int id PK
        string username UK
        string first_name
        string last_name
        string email
        string password "Argon2id / BCrypt hash"
        boolean is_staff
        boolean is_superuser
        datetime date_joined
    }

    ACCOUNT {
        bigint id PK
        int user_id FK "Indexed"
        string name "UK(user_id, name)"
        string account_type "CASH | BANK | WALLET | SAVINGS | CREDIT"
        string currency "USD | ARS | EUR"
        decimal initial_balance
        boolean is_active
        datetime created_at
    }

    CATEGORY {
        bigint id PK
        int user_id FK "Indexed"
        string name "UK(user_id, name)"
        string category_type "INCOME | EXPENSE | BOTH"
        string color "Hex #RRGGBB"
        string icon "Bootstrap Icon"
        text description
        datetime created_at
    }

    TRANSACTION {
        bigint id PK
        int user_id FK "Indexed (user_id, -date)"
        bigint account_id FK
        bigint destination_account_id FK "Nullable (solo TRANSFER)"
        bigint category_id FK "Nullable en TRANSFER"
        string type "INCOME | EXPENSE | TRANSFER"
        decimal amount "CHECK (amount > 0)"
        date date "Indexed"
        text description
        uuid transfer_group_id
        datetime created_at
        datetime updated_at
    }

    BUDGET {
        bigint id PK
        int user_id FK "Indexed (user_id, year, month)"
        bigint category_id FK "UK(user_id, category_id, month, year)"
        decimal amount "CHECK (amount > 0)"
        smallint month "1..12"
        smallint year "2000..2100"
        datetime created_at
    }

    SUPPORT_TICKET {
        bigint id PK
        int user_id FK "Nullable (Visitante o Usuario)"
        string contact_name
        string contact_email
        string ticket_type "SUGGESTION | BUG | LOGIN_ISSUE | OTHER"
        string subject
        text message
        string status "OPEN | IN_REVIEW | PLANNED | RESOLVED"
        text admin_response
        datetime created_at
        datetime updated_at
    }
```

---

## 5. Estrategia de Aislamiento Multi-Usuario (Data Segregation en 4 Capas)

1. **Capa de Controladores (`views.py` / `api_views.py`)**: Todas las rutas financieras y de perfil exigen `@login_required` o `IsAuthenticated` (JWT/Session). El panel `/support/manage/` exige además `is_staff` o `is_superuser` (`403 PermissionDenied`).
2. **Capa de Formularios y Serializers (`forms.py` / `serializers.py`)**: Los campos relacionales (`account`, `destination_account`, `category`) filtran su `queryset` exclusivamente con `.filter(user=request.user)`.
3. **Capa de Servicios y Modelos (`services.py` / `models.py`)**: `TransactionService.validate_ownership()` y `Model.clean()` verifican que `category.user_id == user.id` y `account.user_id == user.id`. Cualquier intento de inyección cruzada registra una alerta en `logs/security_audit.log` y lanza `PermissionDenied`.
4. **Capa de Repositorios (`repositories.py`)**: `get_for_user(user, pk)` aplica `get_object_or_404(..., pk=pk, user=user)`, respondiendo `404 Not Found` ante cualquier intento de ataque **IDOR**.

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
- Updated base template to load SweetAlert2 globally
- Improved overall UX with interactive feedback on delete actions

## [2025-10-18] BudgetBuddy v0.4
- Added transaction editing feature (Update) to complete CRUD operations
- New edit view and template for updating existing records
- Integrated Bootstrap styling and message alerts for edit feedback
- Updated transaction list with edit and delete actions
- Improved UX and code organization for form handling

## [2025-10-18] BudgetBuddy v0.5  
- Implementado sistema completo de autenticación de usuarios  
  (login, logout y registro desde la interfaz principal)  
- Protección de vistas: solo usuarios autenticados pueden acceder a sus transacciones  
- Asociación de registros financieros a cada usuario  
- Nuevo mensaje de confirmación al cerrar sesión (“👋 Sesión cerrada correctamente”)  
- Navbar dinámico:
  - Solo visible tras iniciar sesión  
  - Botón “Admin” visible solo para usuarios staff/superuser  
  - Opción “Cerrar sesión” para todos los usuarios logueados  
- Mejoras de estilo y coherencia visual con Bootstrap  
- Sistema de alertas visuales con mensajes de Django  
- Ajustes menores en estructura de templates y rutas estáticas  

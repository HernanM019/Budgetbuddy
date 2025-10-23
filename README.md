# BudgetBuddy
An application to help myself in controlling my income and expenses.
This project was born with the intention of learning and adapting.

Initially was intended to be a "Vibe Coding" approach, for learning the basics of how an application works. I understood
that reading theory is a slow process of learning, meanwhile using AI to draw an initial sketch might come as a huge 
advantage to understand the skeleton and the very basics.
This is my intent in entering onto this exciting world of WebApp development.

# Roadmap
| Etapa                       | Tema                                                                                                                                                               | Estado                            | Prioridad |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------- | --------- |
| **0. Categorías dinámicas** | Implementar sistema de categorías personalizables (predefinidas por defecto, con opción de agregar/editar/eliminar) y selección desde lista al crear transacciones | 🟢 En curso (nuevo objetivo base) | 🔥 Alta   |
| **1. PostgreSQL**           | Migrar DB desde SQLite a PostgreSQL                                                                                                                                | ⚪ Pendiente siguiente paso        | 🔥 Alta   |
| **2. DRF API**              | Endpoints REST para entidades clave (usuarios, presupuestos, transacciones, categorías)                                                                            | ⚪ Por comenzar                    | Alta      |
| **3. Pandas**               | Análisis de gastos y generación de reportes automáticos                                                                                                            | ⚪ Por comenzar                    | Media     |
| **4. Celery**               | Tareas async (recordatorios, reportes automáticos)                                                                                                                 | ⚪ Por comenzar                    | Media     |
| **5. Docker**               | Deploy local reproducible con `docker-compose` (app + db + redis)                                                                                                  | ⚪ Por comenzar                    | Alta      |
| **6. Testing**              | Pytest / QA (pruebas de funciones críticas y endpoints)                                                                                                            | ⚪ Por comenzar                    | Media     |
| **7. Hosting**              | Deploy online (Railway / Render / AWS)                                                                                                                             | ⚪ Por comenzar                    | Alta      |
| **8. Extras**               | Filtros / Export / **Charts (gráficos visuales de datos)**                                                                                                         | ⚪ Por comenzar                    | Media     |


Internal testings:

to run django server, use: python manage.py runserver

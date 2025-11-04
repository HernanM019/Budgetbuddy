"""
───────────────────────────────────────────────────────────────
BudgetBuddy - URLs de la aplicación 'budget'
───────────────────────────────────────────────────────────────

Este archivo define las rutas *internas* de la app 'budget'.

Cuando el proyecto principal (budgetbuddy/urls.py) hace:
    path('', include('budget.urls'))

todas las rutas listadas aquí se activan bajo el dominio raíz.
Por ejemplo, la ruta '' (vacía) acá significa que visitar:
    http://localhost:8000/
ejecutará la vista 'transaction_list'.

───────────────────────────────────────────────────────────────
Estructura general:
───────────────────────────────────────────────────────────────
path('ruta/', vista_asociada, name='nombre_para_usar_en_templates')

- 'ruta/' -> la parte del URL que Django debe reconocer.
- 'vista_asociada' → la función (o clase) que se ejecutará.
- 'name' -> un alias que puedo usar en plantillas con {% url 'alias' %}.
───────────────────────────────────────────────────────────────
"""

from django.urls import path
# 'path' se usa para definir rutas individuales.

from . import views
# Importamos las vistas (funciones definidas en views.py)
# Cada 'path' llamará a una de esas funciones cuando el usuario visite la URL correspondiente.


# ───────────────────────────────────────────────────────────────
# LISTA DE RUTAS DE LA APLICACIÓN
# ───────────────────────────────────────────────────────────────
urlpatterns = [

    # Página principal: lista de transacciones registradas.
    # URL raíz → http://localhost:8000/
    path(
        '',
        views.transaction_list,
        name='transaction_list'
    ),

    # Formulario para agregar una nueva transacción.
    # http://localhost:8000/add/
    path(
        'add/',
        views.add_transaction,
        name='add_transaction'
    ),

    # Eliminar una transacción existente.
    # <int:pk> -> parámetro dinámico que representa el ID (primary key) de la transacción.
    # Ejemplo: /delete/5/ eliminará la transacción con id=5
    path(
        'delete/<int:pk>/',
        views.delete_transaction,
        name='delete_transaction'
    ),

    # Editar una transacción existente (similar al anterior).
    # http://localhost:8000/edit/7/
    path(
        'edit/<int:pk>/',
        views.edit_transaction,
        name='edit_transaction'
    ),

    # Cerrar sesión manualmente (aunque ya hay logout global en urls.py principal).
    # Este probablemente implemente lógica personalizada, como mostrar mensaje o limpiar sesión.
    path(
        'logout/',
        views.logout_view,
        name='logout'
    ),


    # ───────────────
    # SECCIÓN: Categorías
    # ───────────────

    # Listar todas las categorías disponibles.
    # http://localhost:8000/categories/
    path(
        'categories/',
        views.category_list,
        name='category_list'
    ),

    # Agregar una nueva categoría.
    # http://localhost:8000/categories/add/
    path(
        'categories/add/',
        views.add_category,
        name='add_category'
    ),

    # Editar una categoría existente.
    # Ejemplo: /categories/edit/2/
    path(
        'categories/edit/<int:pk>/',
        views.edit_category,
        name='edit_category'
    ),

    # Eliminar una categoría existente.
    # Ejemplo: /categories/delete/3/
    path(
        'categories/delete/<int:pk>/',
        views.delete_category,
        name='delete_category'
    ),

    # Agregar una categoría de forma asíncrona (AJAX).
    # Esta ruta normalmente es llamada desde JavaScript (fetch, axios, etc.)
    # Sirve crear una categoría sin recargar la página completa.
    path(
        'categories/ajax/add/',
        views.ajax_add_category,
        name='ajax_add_category'
    ),
    """
    Los <int:pk> son capturas de parámetros dinámicos.
    Django los pasa como argumentos a la función vista.
    
    Ejemplo:

def delete_transaction(request, pk):
    # acá pk será, por ejemplo, 5


El name de cada ruta se usa dentro de plantillas y redirecciones.

    Por ejemplo:

<a href="{% url 'add_transaction' %}">Agregar nueva</a>


Si mañana yo cambiara la ruta a 'transactions/add/', no necesitaría modificar los templates.

La ruta 'categories/ajax/add/' es especial: implica que hay código JavaScript haciendo peticiones AJAX a Django (probablemente un fetch() que devuelve JSON).
Es una pista de interacción moderna (sin recargar la página).
    """

]


"""""
COMO FUNCIONA ESTE ARCHIVO:

1) El navegador pide una URL, por ejemplo /categories/add/.

2) Django entra por el archivo principal budgetbuddy/urls.py.

3) El patrón path('', include('budget.urls')) transfiere el control a este archivo.

4) Django encuentra una coincidencia con 'categories/add/'.

5) Ejecuta la función add_category() definida en budget/views.py.

6) Esa vista devuelve una respuesta (HTML o JSON).

7) Django la envía al navegador.
"""
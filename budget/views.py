# Create your views here.
"""
───────────────────────────────────────────────────────────────
BudgetBuddy - views.py
───────────────────────────────────────────────────────────────

Las *views* (vistas) son el “cerebro lógico” de Django.
Reciben una request del navegador, procesan los datos (por ejemplo,
consultas a la base de datos o formularios), y devuelven una respuesta
(HTML, JSON, redirección, etc.).

Aquí se manejan:
    - Autenticación de usuarios (login/logout/register)
    - CRUD de Transacciones (crear, leer, actualizar, eliminar)
    - CRUD de Categorías (con soporte AJAX)

───────────────────────────────────────────────────────────────
"""

# ───────────────────────────────────────────────────────────────
# IMPORTACIONES
# ───────────────────────────────────────────────────────────────
from .models import Transaction, Category  # Modelos de la base de datos
from django.shortcuts import render, redirect, get_object_or_404
# render: muestra plantillas HTML
# redirect: redirige a otra URL
# get_object_or_404: busca un objeto o lanza error 404 si no existe

from django.contrib import messages
# Sistema de mensajes “flash” (éxito, error, etc.) que aparece en la interfaz

from django.contrib.auth.decorators import login_required
# Decorador que bloquea acceso a usuarios no logueados

from django.contrib.auth import login, logout
# Funciones integradas para manejar sesión de usuarios

from .forms import TransactionForm, CustomUserCreationForm, CategoryForm
# Formularios definidos en forms.py que validan datos y crean instancias de modelos

from django.views.decorators.http import require_POST
# Decorador que fuerza que la vista acepte solo peticiones POST (útil en AJAX)

from django.http import JsonResponse
# Permite devolver respuestas JSON (por ejemplo, al usar AJAX en frontend)


# ───────────────────────────────────────────────────────────────
# SECCIÓN: MANEJO DE USUARIOS
# ───────────────────────────────────────────────────────────────

@login_required(login_url='login')
def transaction_list(request):
    """
    Muestra todas las transacciones del usuario autenticado y calcula totales.

    Flujo:
        1. Filtra transacciones según el usuario logueado.
        2. Calcula ingresos, gastos y balance total.
        3. Envía esos datos al template 'transaction_list.html'.

    Template: budget/transaction_list.html
    """
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')

    # Suma total de ingresos y gastos (usa comprensión de listas)
    total_income = sum(t.amount for t in transactions if t.type == 'INCOME')
    total_expense = sum(t.amount for t in transactions if t.type == 'EXPENSE')
    balance = total_income - total_expense

    # Renderiza la plantilla con los datos del contexto
    return render(request, 'budget/transaction_list.html', {
        'transactions': transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
    })


def register(request):
    """
    Crea un nuevo usuario y lo inicia automáticamente en sesión.

    Flujo:
        - Si el method es POST, procesa el formulario.
        - Si el formulario es válido, guarda el nuevo usuario, lo loguea y redirige.
        - Si hay errores, los muestra con 'messages'.
        - Si la request es GET, muestra el formulario vacío.
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Inicia sesión automáticamente
            messages.success(request, f"¡Bienvenido, {user.username}! Tu cuenta fue creada correctamente.")
            return redirect('transaction_list')
        else:
            # Recorre los errores y los muestra uno por uno en pantalla
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = CustomUserCreationForm()
    return render(request, 'budget/register.html', {'form': form})


def logout_view(request):
    """
    Cierra la sesión actual del usuario y lo redirige al login.
    """
    logout(request)
    messages.success(request, "👋 Sesión cerrada correctamente.")
    return redirect('login')


# ───────────────────────────────────────────────────────────────
# SECCIÓN: CRUD DE TRANSACCIONES/REGISTROS
# ───────────────────────────────────────────────────────────────

def add_transaction(request):
    """
    Crea una nueva transacción o registro asociado al usuario actual.

    Flujo:
        - Si el method es POST → procesa el formulario enviado.
        - Si es válido -> guarda en DB, muestra mensaje y redirige.
        - Si es GET -> muestra formulario vacío.
    """
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            messages.success(request, "Registro agregado correctamente.")
            return redirect('transaction_list')
    else:
        form = TransactionForm(user=request.user)
    return render(request, 'budget/add_transaction.html', {'form': form})


def delete_transaction(request, pk):
    """
    Elimina una transacción existente mediante su primary key (pk).

    Flujo:
        - Busca la transacción o lanza error 404 si no existe.
        - Si la request es POST -> la borra de la base de datos.
        - Si fue llamada por AJAX -> devuelve JSON.
        - Si fue llamada por navegador -> muestra mensaje y redirige.
        - Si la request es GET -> muestra confirmación antes de borrar.
    """
    transaction = get_object_or_404(Transaction, pk=pk)
    if request.method == 'POST':
        transaction.delete()

        # Detecta si fue llamada vía AJAX
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        messages.success(request, "Registro eliminado correctamente.")
        return redirect('transaction_list')

    return render(request, 'budget/confirm_delete.html', {'transaction': transaction})


def edit_transaction(request, pk):
    """
    Edita una transacción existente.

    Flujo:
        - Carga el objeto según ID y usuario.
        - Si POST -> valida y guarda cambios.
        - Si GET → muestra el formulario pre-rellenado.
    """
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro actualizado correctamente.")
            return redirect('transaction_list')
    else:
        form = TransactionForm(instance=transaction, user=request.user)
    return render(request, 'budget/edit_transaction.html', {'form': form, 'transaction': transaction})


# ───────────────────────────────────────────────────────────────
# SECCIÓN: CATEGORÍAS
# ───────────────────────────────────────────────────────────────

@login_required
def category_list(request):
    """
    Lista todas las categorías creadas por el usuario actual.
    """
    categories = Category.objects.filter(user=request.user)
    return render(request, 'budget/category_list.html', {'categories': categories})


@login_required
@require_POST
def ajax_add_category(request):
    """
    Agrega una nueva categoría vía AJAX (sin recargar la página).

    Flujo:
        - Requiere login y method POST.
        - Toma los campos enviados por JS (name, description).
        - Valida duplicados y campos vacíos.
        - Crea la categoría en DB.
        - Devuelve JSON con el resultado.
    """
    name = request.POST.get('name')
    description = request.POST.get('description', '')

    if not name:
        return JsonResponse({'success': False, 'error': 'El nombre es obligatorio.'}, status=400)

    # Evita duplicados por usuario
    if Category.objects.filter(user=request.user, name=name).exists():
        return JsonResponse({'success': False, 'error': 'Ya existe una categoría con ese nombre.'}, status=400)

    category = Category.objects.create(user=request.user, name=name, description=description)
    return JsonResponse({'success': True, 'id': category.id, 'name': category.name})


@login_required
def add_category(request):
    """
    Agrega una categoría usando un formulario tradicional (no AJAX).

    Flujo:
        - Si POST → guarda la categoría nueva y redirige.
        - Si GET → muestra formulario vacío.
    """
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'budget/add_category.html', {'form': form})


@login_required
def edit_category(request, pk):
    """
    Edita una categoría existente.
    """
    category = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'budget/edit_category.html', {'form': form, 'category': category})


@login_required
def delete_category(request, pk):
    """
    Elimina una categoría existente (previa confirmación).
    """
    category = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == 'POST':
        category.delete()
        return redirect('category_list')
    return render(request, 'budget/confirm_delete.html', {'object': category})

""""
COMO FUNCIONA:

1) Cada path() en budget/urls.py apunta a una función de este archivo.

2) Las vistas comunican la lógica: base de datos ↔ formulario ↔ template.

3) render() es la puerta de salida: convierte tus datos en una página HTML.

4)) messages comunica feedback entre acciones (por ejemplo, “Transacción creada correctamente”).

5) login_required protege páginas privadas: si no estás logueado, Django te manda al login.
"""
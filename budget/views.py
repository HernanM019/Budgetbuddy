# Create your views here.
from .models import Transaction
from .models import Category
from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth import logout
from .forms import TransactionForm
from .forms import CustomUserCreationForm as UserCreationForm
from .forms import CustomUserCreationForm
from .forms import CategoryForm

#################################### MANEJO DE USUARIOS ##############################

#Login requerido
@login_required(login_url='login')
def transaction_list(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    total_income = sum(t.amount for t in transactions if t.type == 'INCOME')
    total_expense = sum(t.amount for t in transactions if t.type == 'EXPENSE')
    balance = total_income - total_expense

    return render(request, 'budget/transaction_list.html', {
        'transactions': transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
    })

#Registro de usuarios
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # inicia sesión automáticamente tras registrarse
            messages.success(request, f"¡Bienvenido, {user.username}! Tu cuenta fue creada correctamente.")
            return redirect('transaction_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = UserCreationForm()
    return render(request, 'budget/register.html', {'form': form})

#Logout
def logout_view(request):
    logout(request)
    messages.success(request, "👋 Sesión cerrada correctamente.")
    return redirect('login')

#################################### CRUDs ##############################

#CRUD - ADD
def add_transaction(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            messages.success(request, "Registro agregado correctamente.")
            return redirect('transaction_list')
        else:
            for field, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = TransactionForm()

    return render(request, 'budget/add_transaction.html', {'form': form})


from django.http import JsonResponse

#CRUD - DELETE
def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if request.method == 'POST':
        transaction.delete()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        messages.success(request, "Registro eliminado correctamente.")
        return redirect('transaction_list')

    return render(request, 'budget/confirm_delete.html', {'transaction': transaction})

#CRUD - EDIT
def edit_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro actualizado correctamente.")
            return redirect('transaction_list')
        else:
            for field, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = TransactionForm(instance=transaction)

    return render(request, 'budget/edit_transaction.html', {'form': form, 'transaction': transaction})

#################################### CATEGORIES ##############################

@login_required
def category_list(request):
    categories = Category.objects.filter(user=request.user)
    return render(request, 'budget/category_list.html', {'categories': categories})

@login_required
def add_category(request):
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
    category = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == 'POST':
        category.delete()
        return redirect('category_list')
    return render(request, 'budget/confirm_delete.html', {'object': category})
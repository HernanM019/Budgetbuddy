# Create your views here.

from django.shortcuts import render
from .models import Transaction
from django.shortcuts import redirect
from .forms import TransactionForm
from django.contrib import messages
from django.shortcuts import get_object_or_404

def transaction_list(request):
    transactions = Transaction.objects.all().order_by('-date')

    total_income = sum(t.amount for t in transactions if t.type == 'INCOME')
    total_expense = sum(t.amount for t in transactions if t.type == 'EXPENSE')
    balance = total_income - total_expense

    context = {
        'transactions': transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
    }
    return render(request, 'budget/transaction_list.html', context)

def add_transaction(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Transacción registrada correctamente.")
            return redirect('transaction_list')
        else:
            # Si hay error, mostramos el primer mensaje de error del formulario
            for field, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = TransactionForm()

    return render(request, 'budget/add_transaction.html', {'form': form})


from django.http import JsonResponse


def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if request.method == 'POST':
        transaction.delete()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        messages.success(request, "Transacción eliminada correctamente.")
        return redirect('transaction_list')

    return render(request, 'budget/confirm_delete.html', {'transaction': transaction})

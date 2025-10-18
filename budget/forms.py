from django import forms
from .models import Transaction
from datetime import date

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['type', 'category', 'amount', 'date', 'description']
        labels = {
            'type': 'Tipo',
            'category': 'Categoría',
            'amount': 'Monto',
            'date': 'Fecha',
            'description': 'Descripción',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_date(self):
        input_date = self.cleaned_data['date']
        if input_date > date.today():
            raise forms.ValidationError("No se pueden registrar transacciones con fecha futura.")
        return input_date

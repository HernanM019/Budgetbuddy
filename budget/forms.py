from django import forms
from .models import Transaction
from datetime import date

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['type', 'category', 'amount', 'date', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_date(self):
        input_date = self.cleaned_data['date']
        if input_date > date.today():
            raise forms.ValidationError("No se pueden registrar transacciones con fecha futura.")
        return input_date

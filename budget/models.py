# Create your models here.

from django.db import models

class Transaction(models.Model):
    TYPE_CHOICES = [
        ('INCOME', 'Ingreso'),
        ('EXPENSE', 'Gasto'),
    ]

    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    category = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} - {self.category} - ${self.amount}"

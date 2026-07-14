from django.contrib import admin

from expenses.models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("__str__", "category", "amount", "expense_date")
    list_filter = ("category",)
    search_fields = ("car__make", "car__model", "car__registration_number", "vendor")

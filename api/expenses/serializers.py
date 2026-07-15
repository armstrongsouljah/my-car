from rest_framework import serializers

from utils.Serializers import CreateModelSerializer, EditModelSerializer, ListModelSerializer

from expenses.models import Expense


class ExpenseCreateSerializer(CreateModelSerializer):
    class Meta:
        model = Expense
        fields = (
            "car", "category", "amount", "expense_date", "vendor",
            "description", "odometer_km", "litres",
        )


class ExpenseEditSerializer(EditModelSerializer):
    class Meta:
        model = Expense
        fields = (
            "category", "amount", "expense_date", "vendor",
            "description", "odometer_km", "litres",
        )


class ExpenseListSerializer(ListModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Expense
        fields = (
            "id", "car", "category", "category_display", "amount",
            "expense_date", "vendor", "description", "odometer_km", "litres", "created_at",
        )

    @staticmethod
    def select_related_fields():
        return ["car"]


class ExpenseDetailSerializer(ExpenseListSerializer):
    class Meta(ExpenseListSerializer.Meta):
        fields = ExpenseListSerializer.Meta.fields + ("updated_at",)

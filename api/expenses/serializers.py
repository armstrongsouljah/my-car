from rest_framework import serializers

from expenses.models import Expense
from utils.Currency import convert_amount
from utils.Serializers import CreateModelSerializer, EditModelSerializer, ListModelSerializer


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
    """
    display_amount/display_currency convert `amount` (recorded in
    `currency`, see #40) into the requesting owner's own currency, using
    whatever rate table the view put in the serializer context
    (ExpenseListCreateView/ExpenseDetailView's get_serializer_context) —
    falls back to the raw amount, unconverted, whenever either currency is
    unset/unrecognized or no context was given (e.g. a serializer used
    outside a request, like in a test).

    Declared directly here rather than via a mixin: DRF's serializer
    metaclass only collects declared fields from bases that are themselves
    Serializer subclasses, so a plain mixin's fields would silently be
    dropped.
    """
    display_amount = serializers.SerializerMethodField()
    display_currency = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = (
            "id", "car", "category", "amount", "currency", "display_amount", "display_currency",
            "expense_date", "vendor", "description", "odometer_km", "litres",
        )

    @staticmethod
    def select_related_fields():
        return ["car"]

    def _owner_currency(self):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return getattr(user, "currency", "") or ""

    def get_display_currency(self, obj):
        return self._owner_currency()

    def get_display_amount(self, obj):
        rates = self.context.get("rates", {})
        return float(convert_amount(obj.amount, obj.currency, self._owner_currency(), rates))


class ExpenseDetailSerializer(ExpenseListSerializer):
    class Meta(ExpenseListSerializer.Meta):
        fields = ExpenseListSerializer.Meta.fields + ("updated_at",)

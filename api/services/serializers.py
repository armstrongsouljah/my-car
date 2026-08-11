from rest_framework import serializers, status

from services.models import ServiceRecord
from utils.Currency import convert_amount
from utils.Exception import CustomValidation
from utils.Serializers import CreateModelSerializer, EditModelSerializer, ListModelSerializer


class DisplayCostMixin:
    """
    Converts `cost` (recorded in `currency`, see #40) into the requesting
    owner's own currency for display — mirrors expenses.serializers.
    ExpenseListSerializer's display_amount, just for ServiceRecord.cost,
    which (unlike Expense.amount) may be null.

    Only the methods live here, not the SerializerMethodField declarations
    themselves: DRF's serializer metaclass only collects declared fields
    from bases that are themselves Serializer subclasses, so a plain
    mixin's field declarations would silently be dropped — each serializer
    below declares `display_cost`/`display_currency` itself.
    """

    def _owner_currency(self):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return getattr(user, "currency", "") or ""

    def get_display_currency(self, obj):
        return self._owner_currency()

    def get_display_cost(self, obj):
        if obj.cost is None:
            return None
        rates = self.context.get("rates", {})
        return float(convert_amount(obj.cost, obj.currency, self._owner_currency(), rates))


class ServiceRecordCreateSerializer(CreateModelSerializer):
    class Meta:
        model = ServiceRecord
        fields = (
            "car", "service_type", "service_date", "odometer_km", "garage_name",
            "description", "cost", "interval_km", "interval_months",
        )

    def validate(self, attrs):
        if not attrs.get("interval_km") and not attrs.get("interval_months"):
            raise CustomValidation(
                "Set a next-service interval: kilometres, months, or both (whichever comes first applies).",
                field="interval_km",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return attrs


class ServiceRecordEditSerializer(EditModelSerializer):
    class Meta:
        model = ServiceRecord
        fields = (
            "service_type", "service_date", "odometer_km", "garage_name",
            "description", "cost", "interval_km", "interval_months",
        )


class ServiceRecordListSerializer(DisplayCostMixin, ListModelSerializer):
    service_type_display = serializers.CharField(source="get_service_type_display", read_only=True)
    display_cost = serializers.SerializerMethodField()
    display_currency = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRecord
        fields = (
            "id", "service_type_display", "service_date",
            "odometer_km", "garage_name", "description", "cost", "currency", "display_cost", "display_currency",
            "next_due_odometer_km", "next_due_date",
        )

    @staticmethod
    def select_related_fields():
        return ["car"]


class ServiceRecordDetailSerializer(DisplayCostMixin, ListModelSerializer):
    service_type_display = serializers.CharField(source="get_service_type_display", read_only=True)
    display_cost = serializers.SerializerMethodField()
    display_currency = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRecord
        fields = (
            "id", "car", "service_type", "service_type_display", "service_date",
            "odometer_km", "garage_name", "description", "cost", "currency", "display_cost", "display_currency",
            "interval_km", "interval_months",
            "next_due_odometer_km", "next_due_date",
            "created_at", "updated_at",
        )

    @staticmethod
    def select_related_fields():
        return ["car"]

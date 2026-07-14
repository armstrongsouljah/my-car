from rest_framework import serializers, status

from utils.Exception import CustomValidation
from utils.Serializers import CreateModelSerializer, EditModelSerializer, ListModelSerializer

from services.models import ServiceRecord


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


class ServiceRecordListSerializer(ListModelSerializer):
    service_type_display = serializers.CharField(source="get_service_type_display", read_only=True)

    class Meta:
        model = ServiceRecord
        fields = (
            "id", "car", "service_type", "service_type_display", "service_date",
            "odometer_km", "garage_name", "cost", "interval_km", "interval_months",
            "next_due_odometer_km", "next_due_date", "created_at",
        )

    @staticmethod
    def select_related_fields():
        return ["car"]


class ServiceRecordDetailSerializer(ListModelSerializer):
    service_type_display = serializers.CharField(source="get_service_type_display", read_only=True)

    class Meta:
        model = ServiceRecord
        fields = (
            "id", "car", "service_type", "service_type_display", "service_date",
            "odometer_km", "garage_name", "description", "cost",
            "interval_km", "interval_months",
            "next_due_odometer_km", "next_due_date",
            "created_at", "updated_at",
        )

    @staticmethod
    def select_related_fields():
        return ["car"]

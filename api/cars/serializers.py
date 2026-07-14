from rest_framework import serializers, status

from utils.Exception import CustomValidation
from utils.Serializers import CreateModelSerializer, EditModelSerializer, ListModelSerializer

from cars.models import Car


class CarCreateSerializer(CreateModelSerializer):
    class Meta:
        model = Car
        fields = (
            "owner", "make", "model", "year", "registration_number", "vin",
            "color", "fuel_type", "current_odometer_km", "notes",
        )

    def validate(self, attrs):
        registration_number = (attrs.get("registration_number") or "").strip().upper()
        attrs["registration_number"] = registration_number

        if registration_number and Car.objects.filter(
            owner=attrs["owner"], registration_number=registration_number, is_active=True
        ).exists():
            raise CustomValidation(
                "You already have a car with this registration number.",
                field="registration_number",
                status_code=status.HTTP_409_CONFLICT,
            )
        return attrs


class CarEditSerializer(EditModelSerializer):
    class Meta:
        model = Car
        fields = (
            "make", "model", "year", "registration_number", "vin",
            "color", "fuel_type", "current_odometer_km", "notes",
        )

    def validate_current_odometer_km(self, value):
        if self.instance and value < self.instance.current_odometer_km:
            raise CustomValidation(
                "Odometer reading cannot go backwards.",
                field="current_odometer_km",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return value


class CarListSerializer(ListModelSerializer):
    display_name = serializers.CharField(source="__str__", read_only=True)

    class Meta:
        model = Car
        fields = (
            "id", "display_name", "make", "model", "year", "registration_number",
            "color", "fuel_type", "current_odometer_km", "is_active", "created_at",
        )

    @staticmethod
    def select_related_fields():
        return []


class CarDetailSerializer(ListModelSerializer):
    display_name = serializers.CharField(source="__str__", read_only=True)
    reminders = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = (
            "id", "display_name", "make", "model", "year", "registration_number",
            "vin", "color", "fuel_type", "current_odometer_km", "notes",
            "is_active", "reminders", "created_at", "updated_at",
        )

    def get_reminders(self, car):
        from services.reminders import build_car_reminders

        return build_car_reminders(car)

from rest_framework import serializers, status

from utils.Exception import CustomValidation
from utils.Serializers import CreateModelSerializer, EditModelSerializer, ListModelSerializer

from cars.models import Car


class CarCreateSerializer(CreateModelSerializer):
    class Meta:
        model = Car
        fields = (
            "owner", "make", "model", "year", "registration_number", "vin",
            "color", "fuel_type", "photo", "current_odometer_km", "notes",
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
            "color", "fuel_type", "photo", "current_odometer_km", "notes",
        )

    def validate_current_odometer_km(self, value):
        if self.instance and value < self.instance.current_odometer_km:
            raise CustomValidation(
                "Odometer reading cannot go backwards.",
                field="current_odometer_km",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return value

    def update(self, instance, validated_data):
        # current_odometer_km always goes through record_odometer() so the
        # write is atomic against concurrent updates and odometer_updated_at
        # stays in sync (matches the ServiceRecord/Inspection save() path).
        odometer_km = validated_data.pop("current_odometer_km", None)
        instance = super().update(instance, validated_data)
        if odometer_km is not None:
            instance.record_odometer(odometer_km)
        return instance


class CarListSerializer(ListModelSerializer):
    display_name = serializers.CharField(source="__str__", read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = (
            "id", "display_name", "make", "model", "year", "registration_number",
            "color", "fuel_type", "photo_url", "current_odometer_km", "is_active", "created_at",
        )

    def get_photo_url(self, car):
        return car.photo.url if car.photo else None

    @staticmethod
    def select_related_fields():
        return []


class CarDetailSerializer(ListModelSerializer):
    display_name = serializers.CharField(source="__str__", read_only=True)
    photo_url = serializers.SerializerMethodField()
    reminders = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = (
            "id", "display_name", "make", "model", "year", "registration_number",
            "vin", "color", "fuel_type", "photo_url", "current_odometer_km",
            "odometer_updated_at", "notes", "is_active", "reminders",
            "created_at", "updated_at",
        )

    def get_photo_url(self, car):
        return car.photo.url if car.photo else None

    def get_reminders(self, car):
        from services.reminders import build_car_reminders

        return build_car_reminders(car)

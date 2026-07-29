from django.utils import timezone
from rest_framework import serializers, status

from utils.Exception import CustomValidation
from utils.Serializers import CreateModelSerializer, EditModelSerializer, ListModelSerializer

from reminders.engine import evaluate_reminder
from reminders.models import Reminder
from utils import Constants

METHODS_NEEDING_KM = (
    Constants.REMINDER_TRACKING_METHOD_MILEAGE,
    Constants.REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE,
)
METHODS_NEEDING_MONTHS = (
    Constants.REMINDER_TRACKING_METHOD_DATE,
    Constants.REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE,
)


def _validate_tracking_method(attrs, car):
    method = attrs.get("tracking_method")
    needs_km = method in METHODS_NEEDING_KM
    needs_months = method in METHODS_NEEDING_MONTHS

    if needs_km and not attrs.get("interval_km"):
        raise CustomValidation(
            "Set a mileage interval for this tracking method.",
            field="interval_km", status_code=status.HTTP_400_BAD_REQUEST,
        )
    if needs_months and not attrs.get("interval_months"):
        raise CustomValidation(
            "Set a time interval for this tracking method.",
            field="interval_months", status_code=status.HTTP_400_BAD_REQUEST,
        )

    if needs_km and attrs.get("baseline_odometer_km") is None:
        attrs["baseline_odometer_km"] = car.current_odometer_km
    if needs_months and attrs.get("baseline_date") is None:
        attrs["baseline_date"] = timezone.localdate()

    return attrs


class ReminderCreateSerializer(CreateModelSerializer):
    class Meta:
        model = Reminder
        fields = (
            "car", "catalog_key", "title", "category", "is_essential",
            "tracking_method", "interval_km", "interval_months",
            "baseline_odometer_km", "baseline_date", "notes",
        )

    def validate(self, attrs):
        return _validate_tracking_method(attrs, attrs["car"])


class ReminderEditSerializer(EditModelSerializer):
    class Meta:
        model = Reminder
        fields = (
            "title", "category", "is_essential", "tracking_method",
            "interval_km", "interval_months", "baseline_odometer_km",
            "baseline_date", "notes",
        )

    def validate(self, attrs):
        method = attrs.get("tracking_method", self.instance.tracking_method)
        merged = {**{f: getattr(self.instance, f) for f in self.Meta.fields}, **attrs, "tracking_method": method}
        validated = _validate_tracking_method(merged, self.instance.car)
        for key in ("baseline_odometer_km", "baseline_date"):
            if validated.get(key) != getattr(self.instance, key):
                attrs[key] = validated[key]
        return attrs


class ReminderListSerializer(ListModelSerializer):
    status = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Reminder
        fields = (
            "id", "car", "title", "is_essential",
            "baseline_odometer_km", "baseline_date",
            "next_due_odometer_km", "next_due_date",
            "status", "message", "progress_percent",
        )

    def _state(self, instance):
        if not hasattr(instance, "_reminder_state"):
            instance._reminder_state = evaluate_reminder(instance)
        return instance._reminder_state

    def get_status(self, instance):
        return self._state(instance)["status"]

    def get_message(self, instance):
        return self._state(instance)["message"]

    def get_progress_percent(self, instance):
        return self._state(instance)["progress_percent"]

    @staticmethod
    def select_related_fields():
        return ["car"]


class ReminderDetailSerializer(ListModelSerializer):
    """Fields the edit form (ReminderDetailsForm.jsx) actually reads/writes —
    deliberately not a superset of ReminderListSerializer, which needs
    computed status/progress fields the edit form doesn't render."""

    class Meta:
        model = Reminder
        fields = (
            "id", "car", "catalog_key", "title", "tracking_method",
            "interval_km", "interval_months", "baseline_odometer_km",
            "baseline_date", "notes",
        )

    @staticmethod
    def select_related_fields():
        return ["car"]

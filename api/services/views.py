from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from utils import Cache, Constants, QueryParams
from utils.Exception import CustomValidation
from utils.Views import SmartDetailView, SmartPaginationAPIView, SmartAPIView

from cars.models import Car
from reminders.catalog import OIL_CHANGE_KEY
from services.models import ServiceRecord
from services.reminders import build_car_reminders
from services.serializers import (
    ServiceRecordCreateSerializer,
    ServiceRecordEditSerializer,
    ServiceRecordListSerializer,
    ServiceRecordDetailSerializer,
)


class ServiceRecordListCreateView(SmartPaginationAPIView):
    """
    GET  — service history for the owner's cars (?car=<uuid> to scope to one).
    POST — log a service with its next-service interval rule.
    """
    model = ServiceRecord
    create_serializer = ServiceRecordCreateSerializer
    list_serializer = ServiceRecordListSerializer
    detail_serializer = ServiceRecordDetailSerializer
    permission_classes = [IsAuthenticated]

    def override_post_data(self, data):
        data = dict(data)
        car_id = data.get("car")
        if not Car.objects.filter(pk=car_id, owner=self.request.user).exists():
            raise CustomValidation(
                "Car not found in your garage.",
                field="car",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return data

    def post_response(self, data, instance=None):
        if instance:
            # Reminders are embedded in the cached car detail — refresh it.
            Cache.invalidate_car(instance.car_id, instance.car.owner_id)
        return super().post_response(data, instance=instance)

    def filter_queryset(self, **kwargs):
        return ServiceRecord.objects.filter(car__owner=self.request.user)

    def add_filters(self, queryset):
        car_id = QueryParams.get_str(self.request, "car")
        if car_id:
            queryset = queryset.filter(car_id=car_id)
        service_type = QueryParams.get_str(self.request, "service_type")
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        return queryset


class ServiceRecordDetailView(SmartDetailView):
    model = ServiceRecord
    deletable = True
    detail_serializer = ServiceRecordDetailSerializer
    edit_serializer = ServiceRecordEditSerializer
    permission_classes = [IsAuthenticated]

    def queryset(self, **kwargs):
        return ServiceRecord.objects.filter(pk=kwargs.get("pk"), car__owner=self.request.user)

    def patch_response(self, instance, data):
        Cache.invalidate_car(instance.car_id, instance.car.owner_id)
        return super().patch_response(instance, data)

    def handle_delete(self, model_instance):
        Cache.invalidate_car(model_instance.car_id, model_instance.car.owner_id)
        model_instance.delete()


class RemindersView(SmartAPIView):
    """
    GET — reminder digest across the owner's active cars: next service due
    (km/months, whichever comes first) and general inspection status.

    Only surfaces reminders that need attention (skips "ok" ones — this is a
    nudge list, not a full status report), and skips the generic "next
    service" reminder entirely when the owner already has a dedicated
    oil-change catalog reminder, since the two would otherwise say the same
    thing twice.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, **kwargs):
        cars = Car.objects.filter(owner=request.user, is_active=True)

        payload = []
        for car in cars:
            has_oil_change_reminder = car.reminders.filter(catalog_key=OIL_CHANGE_KEY).exists()
            reminders = [
                r for r in build_car_reminders(car)
                if r["status"] != Constants.REMINDER_STATUS_OK
                and not (r["kind"] == "service" and has_oil_change_reminder)
            ]

            payload.append({
                "car_id": str(car.pk),
                "make": car.make,
                "model": car.model,
                "year": car.year,
                "registration_number": car.registration_number,
                "current_odometer_km": car.current_odometer_km,
                "reminders": reminders,
            })

        return Response(payload, status=status.HTTP_200_OK)

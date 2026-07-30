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
    GET  — service history for the owner's cars (?car=<uuid> to scope to one;
           the `?car=`-only response is Redis-cached until midnight).
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
            Cache.invalidate_service_list(instance.car_id)
            Cache.invalidate_service_digest(instance.car.owner_id)
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

    def get(self, request, *args, **kwargs):
        # Only the `?car=`-scoped request (the frontend's only real usage) is
        # cacheable — anything else (unfiltered, or filtered by service_type)
        # bypasses the cache.
        car_id = QueryParams.get_str(request, "car")
        is_car_only_request = car_id and len(request.query_params) == 1
        if is_car_only_request:
            if not Car.objects.filter(pk=car_id, owner=request.user).exists():
                return super().get(request, *args, **kwargs)
            cached = Cache.get_service_list(car_id)
            if cached is not None:
                return Response(cached, status=status.HTTP_200_OK)

        response = super().get(request, *args, **kwargs)

        if is_car_only_request and response.status_code == status.HTTP_200_OK:
            Cache.set_service_list(car_id, response.data)
        return response


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
        Cache.invalidate_service_list(instance.car_id)
        Cache.invalidate_service_digest(instance.car.owner_id)
        return super().patch_response(instance, data)

    def handle_delete(self, model_instance):
        car_id, owner_id = model_instance.car_id, model_instance.car.owner_id
        Cache.invalidate_car(car_id, owner_id)
        model_instance.delete()
        Cache.invalidate_service_list(car_id)
        Cache.invalidate_service_digest(owner_id)


class RemindersView(SmartAPIView):
    """
    GET — reminder digest across the owner's active cars: next service due
    (km/months, whichever comes first) and general inspection status.
    Redis-cached until midnight (see utils.Cache) — status/progress here are
    computed from today's date and the car's current odometer, not just from
    what's in the database, so a day passing (or an odometer/service/
    inspection update) can change the response with no write of its own.

    Only surfaces reminders that need attention (skips "ok" ones — this is a
    nudge list, not a full status report), and skips the generic "next
    service" reminder entirely when the owner already has a dedicated
    oil-change catalog reminder, since the two would otherwise say the same
    thing twice.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, **kwargs):
        cached = Cache.get_service_digest(request.user.pk)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

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

        Cache.set_service_digest(request.user.pk, payload)
        return Response(payload, status=status.HTTP_200_OK)

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from utils import Cache, QueryParams
from utils.Exception import CustomValidation
from utils.Views import SmartAPIView, SmartDetailView, SmartPaginationAPIView

from cars.models import Car
from reminders.catalog import OIL_CHANGE_KEY, get_reminder_catalog
from reminders.models import Reminder
from reminders.serializers import (
    ReminderCreateSerializer,
    ReminderEditSerializer,
    ReminderListSerializer,
    ReminderDetailSerializer,
)


class ReminderListCreateView(SmartPaginationAPIView):
    """
    GET  — the owner's reminders (?car=<uuid>, ?category=, ?is_essential=).
           The unfiltered response is Redis-cached until midnight.
    POST — create a preset-based or custom reminder for one of the owner's cars.
    """
    model = Reminder
    create_serializer = ReminderCreateSerializer
    list_serializer = ReminderListSerializer
    detail_serializer = ReminderDetailSerializer
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
            Cache.invalidate_reminders(instance.car.owner_id)
            if instance.catalog_key == OIL_CHANGE_KEY:
                # The service digest (GET /services/reminders/) suppresses its
                # generic "next service" nudge when an oil-change catalog
                # reminder exists — creating one changes that response too.
                Cache.invalidate_service_digest(instance.car.owner_id)
        return super().post_response(data, instance=instance)

    def filter_queryset(self, **kwargs):
        return Reminder.objects.filter(car__owner=self.request.user)

    def add_filters(self, queryset):
        car_id = QueryParams.get_str(self.request, "car")
        if car_id:
            queryset = queryset.filter(car_id=car_id)
        category = QueryParams.get_str(self.request, "category")
        if category:
            queryset = queryset.filter(category=category)
        is_essential = QueryParams.get_bool(self.request, "is_essential")
        if is_essential is not None:
            queryset = queryset.filter(is_essential=is_essential)
        return queryset

    def get(self, request, *args, **kwargs):
        is_default_request = not request.query_params
        if is_default_request:
            cached = Cache.get_reminders(request.user.pk)
            if cached is not None:
                return Response(cached, status=status.HTTP_200_OK)

        response = super().get(request, *args, **kwargs)

        if is_default_request and response.status_code == status.HTTP_200_OK:
            Cache.set_reminders(request.user.pk, response.data)
        return response


class ReminderDetailView(SmartDetailView):
    model = Reminder
    deletable = True
    detail_serializer = ReminderDetailSerializer
    edit_serializer = ReminderEditSerializer
    permission_classes = [IsAuthenticated]

    def queryset(self, **kwargs):
        return Reminder.objects.filter(pk=kwargs.get("pk"), car__owner=self.request.user)

    def patch_response(self, instance, data):
        Cache.invalidate_reminders(instance.car.owner_id)
        return super().patch_response(instance, data)

    def handle_delete(self, model_instance):
        owner_id = model_instance.car.owner_id
        is_oil_change = model_instance.catalog_key == OIL_CHANGE_KEY
        model_instance.delete()
        Cache.invalidate_reminders(owner_id)
        if is_oil_change:
            Cache.invalidate_service_digest(owner_id)


class ReminderCatalogView(SmartAPIView):
    """GET — static catalog of preset reminder types, grouped by category (Redis-cached)."""
    permission_classes = [AllowAny]

    def get(self, request, **kwargs):
        cached = Cache.get_reminder_catalog()
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        data = get_reminder_catalog()
        Cache.set_reminder_catalog(data)
        return Response(data, status=status.HTTP_200_OK)

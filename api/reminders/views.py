from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from utils import QueryParams
from utils.Exception import CustomValidation
from utils.Views import SmartAPIView, SmartDetailView, SmartPaginationAPIView

from cars.models import Car
from reminders.catalog import get_reminder_catalog
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


class ReminderDetailView(SmartDetailView):
    model = Reminder
    deletable = True
    detail_serializer = ReminderDetailSerializer
    edit_serializer = ReminderEditSerializer
    permission_classes = [IsAuthenticated]

    def queryset(self, **kwargs):
        return Reminder.objects.filter(pk=kwargs.get("pk"), car__owner=self.request.user)


class ReminderCatalogView(SmartAPIView):
    """GET — static catalog of preset reminder types, grouped by category."""
    permission_classes = [AllowAny]

    def get(self, request, **kwargs):
        return Response(get_reminder_catalog(), status=status.HTTP_200_OK)

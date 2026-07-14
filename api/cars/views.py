from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from utils import Cache, QueryParams
from utils.Views import SmartDetailView, SmartPaginationAPIView

from cars.models import Car
from cars.serializers import (
    CarCreateSerializer,
    CarEditSerializer,
    CarListSerializer,
    CarDetailSerializer,
)


class CarListCreateView(SmartPaginationAPIView):
    """
    GET  — list the authenticated owner's cars (Redis-cached until invalidated).
    POST — register a new car; owners can track as many cars as they like.
    """
    model = Car
    create_serializer = CarCreateSerializer
    list_serializer = CarListSerializer
    detail_serializer = CarDetailSerializer
    permission_classes = [IsAuthenticated]

    def override_post_data(self, data):
        data = dict(data)
        data["owner"] = self.request.user.pk
        return data

    def post_response(self, data, instance=None):
        if instance:
            Cache.invalidate_owner(instance.owner_id)
        return super().post_response(data, instance=instance)

    def filter_queryset(self, **kwargs):
        return Car.objects.filter(owner=self.request.user, is_active=True)

    def add_filters(self, queryset):
        make = QueryParams.get_str(self.request, "make")
        if make:
            queryset = queryset.filter(make__icontains=make)
        return queryset

    def get(self, request, *args, **kwargs):
        # Serve the un-filtered, un-paginated default from Redis when possible.
        is_default_request = not request.query_params
        if is_default_request:
            cached = Cache.get_car_list(request.user.pk)
            if cached is not None:
                return Response(cached, status=status.HTTP_200_OK)

        response = super().get(request, *args, **kwargs)

        if is_default_request and response.status_code == status.HTTP_200_OK:
            Cache.set_car_list(request.user.pk, response.data)
        return response


class CarDetailView(SmartDetailView):
    """
    GET    — car detail with computed reminders (Redis-cached).
    PATCH  — update car info / odometer; invalidates the cache.
    DELETE — remove the car from the owner's garage.
    """
    model = Car
    deletable = True
    detail_serializer = CarDetailSerializer
    edit_serializer = CarEditSerializer
    permission_classes = [IsAuthenticated]

    def queryset(self, **kwargs):
        return Car.objects.filter(pk=kwargs.get("pk"), owner=self.request.user)

    def get(self, request, *args, **kwargs):
        cached = Cache.get_car_detail(kwargs.get("pk"))
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        response = super().get(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            Cache.set_car_detail(kwargs.get("pk"), response.data)
        return response

    def patch_response(self, instance, data):
        Cache.invalidate_car(instance.pk, instance.owner_id)
        return super().patch_response(instance, data)

    def handle_delete(self, model_instance):
        Cache.invalidate_car(model_instance.pk, model_instance.owner_id)
        model_instance.delete()

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from utils import Cache, QueryParams
from utils.Exception import CustomValidation
from utils.Views import SmartDetailView, SmartPaginationAPIView

from cars.models import Car
from inspections.models import Inspection
from inspections.serializers import (
    InspectionCreateSerializer,
    InspectionEditSerializer,
    InspectionListSerializer,
    InspectionDetailSerializer,
)


class InspectionListCreateView(SmartPaginationAPIView):
    """
    GET  — inspection history for the owner's cars (?car=<uuid> to scope;
           that response is Redis-cached until midnight).
    POST — log a general inspection; the report file upload is optional
           (multipart/form-data with a `report` file field).
    """
    model = Inspection
    create_serializer = InspectionCreateSerializer
    list_serializer = InspectionListSerializer
    detail_serializer = InspectionDetailSerializer
    permission_classes = [IsAuthenticated]

    def override_post_data(self, data):
        # request.data may be an immutable QueryDict when multipart.
        if hasattr(data, "dict"):
            files = {key: data[key] for key in data if hasattr(data[key], "read")}
            data = data.dict()
            data.update(files)
        else:
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
            Cache.invalidate_car(instance.car_id, instance.car.owner_id)
            Cache.invalidate_inspection_list(instance.car_id)
            Cache.invalidate_service_digest(instance.car.owner_id)
        return super().post_response(data, instance=instance)

    def filter_queryset(self, **kwargs):
        return Inspection.objects.filter(car__owner=self.request.user)

    def add_filters(self, queryset):
        car_id = QueryParams.get_str(self.request, "car")
        if car_id:
            queryset = queryset.filter(car_id=car_id)
        return queryset

    def get(self, request, *args, **kwargs):
        car_id = QueryParams.get_str(request, "car")
        is_car_only_request = car_id and len(request.query_params) == 1
        if is_car_only_request:
            cached = Cache.get_inspection_list(car_id)
            if cached is not None:
                return Response(cached, status=status.HTTP_200_OK)

        response = super().get(request, *args, **kwargs)

        if is_car_only_request and response.status_code == status.HTTP_200_OK:
            Cache.set_inspection_list(car_id, response.data)
        return response


class InspectionDetailView(SmartDetailView):
    model = Inspection
    deletable = True
    detail_serializer = InspectionDetailSerializer
    edit_serializer = InspectionEditSerializer
    permission_classes = [IsAuthenticated]

    def queryset(self, **kwargs):
        return Inspection.objects.filter(pk=kwargs.get("pk"), car__owner=self.request.user)

    def patch_response(self, instance, data):
        Cache.invalidate_car(instance.car_id, instance.car.owner_id)
        Cache.invalidate_inspection_list(instance.car_id)
        Cache.invalidate_service_digest(instance.car.owner_id)
        return super().patch_response(instance, data)

    def handle_delete(self, model_instance):
        car_id, owner_id = model_instance.car_id, model_instance.car.owner_id
        Cache.invalidate_car(car_id, owner_id)
        model_instance.delete()
        Cache.invalidate_inspection_list(car_id)
        Cache.invalidate_service_digest(owner_id)

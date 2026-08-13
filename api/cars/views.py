import re

from django.http import HttpResponse
from django.template.loader import render_to_string
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from rest_framework.permissions import AllowAny

from utils import Cache, QueryParams
from utils.Exception import CustomValidation
from utils.Views import SmartAPIView, SmartDetailView, SmartPaginationAPIView

from cars.catalog import get_catalog
from cars.models import Car
from cars.reports import build_service_history_report
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
            # Same staleness as the delete path (see #134) -- without this a
            # newly added car's reminders digest doesn't show up on the
            # Reminders/dashboard pages until the cache naturally expires.
            Cache.invalidate_service_digest(instance.owner_id)
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


class CarBulkCreateView(SmartAPIView):
    """
    POST — register several cars in one request: `{"cars": [{...}, {...}]}`.
    Each row runs through CarCreateSerializer independently (same rules as
    the single-car endpoint, including the per-owner registration-number
    uniqueness check), so one bad row doesn't block the rest — the response
    reports created cars and per-row errors side by side.
    """
    permission_classes = [IsAuthenticated]
    max_cars = 20

    def post(self, request, *args, **kwargs):
        rows = request.data.get("cars") if isinstance(request.data, dict) else None
        if not isinstance(rows, list) or not rows:
            raise CustomValidation(
                "Provide a non-empty list of cars under the 'cars' key.",
                field="cars",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if len(rows) > self.max_cars:
            raise CustomValidation(
                f"You can register at most {self.max_cars} cars at once.",
                field="cars",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        created = []
        errors = []
        for index, row in enumerate(rows):
            data = dict(row) if isinstance(row, dict) else {}
            data["owner"] = request.user.pk
            serializer = CarCreateSerializer(data=data)
            try:
                if serializer.is_valid():
                    instance = serializer.save()
                    created.append(CarDetailSerializer(instance).data)
                else:
                    errors.append({"index": index, "errors": serializer.errors})
            except CustomValidation as exc:
                # validate() raises this directly (e.g. duplicate registration
                # number) rather than going through serializer.errors — catch
                # per row so one bad row doesn't abort the rest of the batch.
                errors.append({"index": index, "errors": exc.detail})
            except Exception:
                # Any other per-row failure (e.g. a DB-level integrity error)
                # must not abort the batch — record it and continue.
                errors.append(
                    {"index": index, "errors": {"non_field_errors": ["Could not create this car."]}}
                )

        if created:
            Cache.invalidate_owner(request.user.pk)

        return Response(
            {"created": created, "errors": errors},
            status=status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST,
        )


class CarCatalogView(SmartAPIView):
    """
    GET — static catalog of popular brands with their common models, plus the
    selectable year range (1980..current). Backing this with a live source
    (e.g. NHTSA vPIC) later won't change the response shape.
    """
    permission_classes = [AllowAny]

    def get(self, request, **kwargs):
        return Response(get_catalog(), status=status.HTTP_200_OK)


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
        # An odometer update is exactly what flips a reminder's computed
        # status (ok -> due_soon -> overdue) -- without this the digest
        # (cached until midnight, see #134) can keep showing yesterday's
        # status for a whole day after the reading that should have changed it.
        Cache.invalidate_service_digest(instance.owner_id)
        return super().patch_response(instance, data)

    def handle_delete(self, model_instance):
        Cache.invalidate_car(model_instance.pk, model_instance.owner_id)
        # Without this, a deleted car's entry in the /services/reminders/
        # digest (Redis-cached until midnight) lingers until the cache
        # naturally expires -- it keeps showing on the Reminders page, and
        # navigating into it 404s (see #134).
        Cache.invalidate_service_digest(model_instance.owner_id)
        model_instance.delete()


class CarServiceHistoryReportPDFView(SmartAPIView):
    """
    GET /cars/<uuid:pk>/service-history/pdf/ — a shareable, printable record
    of everything maintenance-relevant logged for this car (service records,
    inspections, maintenance-flavored expenses) — see #62. For handing to a
    buyer as proof of upkeep; the owner downloads and shares it however they
    like, there's no separate public/no-login link.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, **kwargs):
        car = Car.objects.filter(pk=pk, owner=request.user).first()
        if not car:
            return self.not_found()

        # Lazy import — see ExpenseMonthlyReportPDFView (expenses/views.py)
        # for why: keeps this module import-safe (no WeasyPrint/Pango load)
        # for every request that isn't downloading a PDF.
        from weasyprint import HTML

        report = build_service_history_report(car)
        html = render_to_string("reports/car_service_history_report.html", {"report": report})
        pdf_bytes = HTML(string=html).write_pdf()

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        # make/model are free-text fields with no character restrictions --
        # strip down to a safe filename charset rather than trust them
        # straight into a quoted header value.
        safe_name = re.sub(r"[^A-Za-z0-9]+", "-", f"{car.make}-{car.model}").strip("-") or "car"
        response["Content-Disposition"] = f'attachment; filename="glavbox-{safe_name}-service-history.pdf"'
        return response

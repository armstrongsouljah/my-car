from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from cars.models import Car
from expenses.models import Expense
from history_import.duplicates import find_duplicate
from history_import.extraction import ExtractionError, extract_records
from history_import.serializers import ExtractRequestSerializer, ImportRequestSerializer
from services.models import ServiceRecord
from utils import Cache, Constants
from utils.Exception import CustomValidation
from utils.Views import SmartAPIView


def _get_owned_car(car_id, user):
    car = Car.objects.filter(pk=car_id, owner=user).first()
    if not car:
        raise CustomValidation("Car not found in your garage.", field="car", status_code=status.HTTP_404_NOT_FOUND)
    return car


class ServiceHistoryExtractView(SmartAPIView):
    """
    POST /history-import/extract/ — multipart {car, file}. Extracts
    proposed ServiceRecord/Expense rows from an uploaded document (PDF,
    .docx, .xlsx) via Gemini — see #103. Nothing is saved yet; the owner
    reviews/edits the response and confirms via ServiceHistoryImportView.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, **kwargs):
        serializer = ExtractRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        car = _get_owned_car(serializer.validated_data["car"], request.user)

        try:
            records = extract_records(serializer.validated_data["file"])
        except ExtractionError as err:
            raise CustomValidation(str(err), field="file", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # See history_import.duplicates — flagged here so the owner can see
        # and deselect it in the review step; ServiceHistoryImportView also
        # re-checks at confirm time as a hard backstop either way.
        for record in records:
            record["possible_duplicate"] = find_duplicate(car, record) is not None

        return Response({"car": car.id, "records": records}, status=status.HTTP_200_OK)


class ServiceHistoryImportView(SmartAPIView):
    """
    POST /history-import/confirm/ — {car, records: [...]}, each shaped like
    ServiceHistoryExtractView's response rows (owner-reviewed/edited first).
    Creates a real ServiceRecord or Expense per record — see #103.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, **kwargs):
        serializer = ImportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        car = _get_owned_car(serializer.validated_data["car"], request.user)

        service_records_created = 0
        expenses_created = 0
        duplicates_skipped = 0
        for record in serializer.validated_data["records"]:
            # Hard backstop regardless of what the frontend sent — see
            # history_import.duplicates. Catches a duplicate the owner
            # didn't uncheck, or a stale/re-submitted review payload.
            if find_duplicate(car, record) is not None:
                duplicates_skipped += 1
                continue

            if record["kind"] == "part_purchase":
                Expense.objects.create(
                    car=car,
                    category=Constants.EXPENSE_CATEGORY_PARTS,
                    amount=record["cost"] or 0,
                    expense_date=record["date"],
                    vendor=record["vendor"],
                    description=record["description"],
                )
                expenses_created += 1
            else:
                # odometer_km is required on ServiceRecord but often isn't
                # stated on an old invoice — 0 is safe: record_odometer()
                # only ever moves the car's odometer forward, so it can't
                # corrupt the car's real current reading (see cars/models.py).
                ServiceRecord.objects.create(
                    car=car,
                    service_type=record["service_type"] or Constants.SERVICE_TYPE_OTHER,
                    service_date=record["date"],
                    odometer_km=record["odometer_km"] or 0,
                    garage_name=record["vendor"],
                    description=record["description"],
                    cost=record["cost"],
                )
                service_records_created += 1

        if service_records_created or expenses_created:
            Cache.invalidate_owner(request.user.pk)
            Cache.invalidate_car(car.pk, car.owner_id)

        return Response(
            {
                "service_records_created": service_records_created,
                "expenses_created": expenses_created,
                "duplicates_skipped": duplicates_skipped,
            },
            status=status.HTTP_201_CREATED,
        )

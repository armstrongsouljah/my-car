from rest_framework import serializers

from utils import Constants
from utils.Uploads import validate_history_import_upload


class ExtractRequestSerializer(serializers.Serializer):
    car = serializers.UUIDField()
    file = serializers.FileField(validators=[validate_history_import_upload])


class ExtractedRecordSerializer(serializers.Serializer):
    """
    Shape of one record as proposed by history_import.extraction and (after
    the owner reviews/edits it in the frontend) submitted back to
    ServiceHistoryImportView to actually create it — see #103.
    """
    kind = serializers.ChoiceField(choices=["service", "part_purchase"])
    date = serializers.DateField()
    vendor = serializers.CharField(allow_blank=True, required=False, default="")
    description = serializers.CharField(allow_blank=True, required=False, default="")
    cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True, default=None)
    odometer_km = serializers.IntegerField(required=False, allow_null=True, default=None, min_value=0)
    service_type = serializers.ChoiceField(
        choices=Constants.SERVICE_TYPES, required=False, allow_null=True, default=None,
    )


class ImportRequestSerializer(serializers.Serializer):
    car = serializers.UUIDField()
    records = ExtractedRecordSerializer(many=True, allow_empty=False)

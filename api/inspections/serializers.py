from rest_framework import serializers

from utils.Serializers import CreateModelSerializer, EditModelSerializer, ListModelSerializer

from inspections.models import Inspection


class InspectionCreateSerializer(CreateModelSerializer):
    class Meta:
        model = Inspection
        fields = (
            "car", "inspection_date", "odometer_km", "status", "inspector_name",
            "notes", "report", "next_inspection_date",
        )


class InspectionEditSerializer(EditModelSerializer):
    class Meta:
        model = Inspection
        fields = (
            "inspection_date", "odometer_km", "status", "inspector_name",
            "notes", "report", "next_inspection_date",
        )


class InspectionListSerializer(ListModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    report_url = serializers.SerializerMethodField()

    class Meta:
        model = Inspection
        fields = (
            "id", "inspection_date", "status_display",
            "inspector_name", "notes", "report_url", "next_inspection_date",
        )

    def get_report_url(self, instance):
        if not instance.report:
            return None
        return instance.report.url

    @staticmethod
    def select_related_fields():
        return ["car"]


class InspectionDetailSerializer(InspectionListSerializer):
    class Meta(InspectionListSerializer.Meta):
        # "notes" is already in the list serializer's fields (see #114) --
        # only "updated_at" is actually detail-only now.
        fields = InspectionListSerializer.Meta.fields + ("updated_at",)

from rest_framework import serializers

from utils import Constants
from utils.Serializers import ValidateSerializer


class SupportRequestSerializer(ValidateSerializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    subject = serializers.ChoiceField(choices=Constants.SUPPORT_SUBJECTS)
    custom_subject = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    message = serializers.CharField()

    def validate(self, attrs):
        if attrs["subject"] == Constants.SUPPORT_SUBJECT_OTHER and not attrs.get("custom_subject", "").strip():
            raise serializers.ValidationError({"custom_subject": "Please tell us what this is about."})
        return attrs

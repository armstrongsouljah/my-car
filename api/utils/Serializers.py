from rest_framework import serializers


class BaseSerializer(serializers.Serializer):
    def optimize(self, queryset):
        return queryset.select_related(
            *self.get_select_related()).prefetch_related(
            *self.get_prefetch_related())

    @staticmethod
    def get_select_related():
        return []

    @staticmethod
    def get_prefetch_related():
        return []


class BaseModelSerializer(serializers.ModelSerializer):
    class Meta:
        pass

    def optimize(self, queryset):
        return queryset.select_related(*self.select_related_fields()).prefetch_related(*self.prefetch_related_fields())

    @staticmethod
    def select_related_fields():
        return []

    @staticmethod
    def prefetch_related_fields():
        return []


class CreateModelSerializer(BaseModelSerializer):
    class Meta:
        pass

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Update is not supported by create serializers")


class EditModelSerializer(BaseModelSerializer):
    def create(self, validated_data):
        raise serializers.ValidationError("Create is not supported by edit serializers")


class ListModelSerializer(BaseModelSerializer):
    def create(self, validated_data):
        raise serializers.ValidationError("Create is not supported by list serializers")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Update is not supported by list serializers")


class ValidateModelSerializer(ListModelSerializer):
    pass


class ValidateSerializer(BaseSerializer):
    def create(self, _validated_data):
        raise serializers.ValidationError("Create is not supported by validate serializers")

    def update(self, _instance, _validated_data):
        raise serializers.ValidationError("Update is not supported by validate serializers")

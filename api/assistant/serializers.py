from rest_framework import serializers

from utils.Serializers import CreateModelSerializer, ListModelSerializer

from assistant.models import Conversation, Message


class ConversationCreateSerializer(CreateModelSerializer):
    class Meta:
        model = Conversation
        fields = ("owner", "car", "title")


class MessageListSerializer(ListModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "role", "content", "tool_calls", "created_at")


class ConversationListSerializer(ListModelSerializer):
    class Meta:
        model = Conversation
        fields = ("id", "car", "title", "created_at", "updated_at")

    @staticmethod
    def select_related_fields():
        return ["car"]


class ConversationDetailSerializer(ConversationListSerializer):
    messages = MessageListSerializer(many=True, read_only=True)

    class Meta(ConversationListSerializer.Meta):
        fields = ConversationListSerializer.Meta.fields + ("messages",)

    @staticmethod
    def prefetch_related_fields():
        return ["messages"]

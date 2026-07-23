import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import UserRateThrottle

from utils import Constants, QueryParams
from utils.Exception import CustomValidation
from utils.Views import SmartAPIView, SmartDetailView, SmartPaginationAPIView

from cars.models import Car
from assistant.gemini import run_chat
from assistant.models import Conversation, Message
from assistant.serializers import (
    ConversationCreateSerializer,
    ConversationDetailSerializer,
    ConversationListSerializer,
    MessageListSerializer,
)
from assistant.tools import ToolContext

logger = logging.getLogger(__name__)


class ChatThrottle(UserRateThrottle):
    """LLM calls cost money per token — cap message sends per user."""
    scope = "assistant_chat"


class ConversationListCreateView(SmartPaginationAPIView):
    """
    GET  — the owner's conversations (?car=<uuid> to scope to one car).
    POST — start a conversation, pinned to a car in the owner's garage.
    """
    model = Conversation
    create_serializer = ConversationCreateSerializer
    list_serializer = ConversationListSerializer
    detail_serializer = ConversationDetailSerializer
    permission_classes = [IsAuthenticated]

    def override_post_data(self, data):
        data = dict(data)
        car_id = data.get("car")
        car = Car.objects.filter(pk=car_id, owner=self.request.user, is_active=True).first()
        if car is None:
            raise CustomValidation(
                "Car not found in your garage.", field="car", status_code=status.HTTP_404_NOT_FOUND
            )
        data["owner"] = self.request.user.pk
        if not data.get("title"):
            data["title"] = f"{car.make} {car.model}"
        return data

    def filter_queryset(self, **kwargs):
        return Conversation.objects.filter(owner=self.request.user)

    def add_filters(self, queryset):
        car_id = QueryParams.get_str(self.request, "car")
        if car_id:
            queryset = queryset.filter(car_id=car_id)
        return queryset


class ConversationDetailView(SmartDetailView):
    """GET — a conversation with its full message history. DELETE — remove it."""
    model = Conversation
    deletable = True
    detail_serializer = ConversationDetailSerializer
    permission_classes = [IsAuthenticated]

    def queryset(self, **kwargs):
        return Conversation.objects.filter(pk=kwargs.get("pk"), owner=self.request.user)


class MessageListCreateView(SmartAPIView):
    """
    GET  — messages in a conversation.
    POST — send a message; runs the Gemini tool-calling loop grounded in the
           conversation's car, persists both turns, and returns the reply.
    """
    permission_classes = [IsAuthenticated]

    def get_throttles(self):
        # Only throttle sends, not reads.
        if self.request.method == "POST":
            return [ChatThrottle()]
        return []

    def get_conversation(self, pk):
        return (
            Conversation.objects.select_related("car")
            .filter(pk=pk, owner=self.request.user)
            .first()
        )

    def get(self, request, pk, **kwargs):
        conversation = self.get_conversation(pk)
        if conversation is None:
            return self.not_found()
        messages = conversation.messages.all()
        return Response(MessageListSerializer(messages, many=True).data, status=status.HTTP_200_OK)

    def post(self, request, pk, **kwargs):
        conversation = self.get_conversation(pk)
        if conversation is None:
            return self.not_found()

        user_text = (request.data.get("content") or "").strip()
        if not user_text:
            raise CustomValidation("Message content is required.", field="content")
        if len(user_text) > 4000:
            raise CustomValidation("Message is too long.", field="content")

        history = list(
            conversation.messages.filter(
                role__in=[Constants.ASSISTANT_ROLE_USER, Constants.ASSISTANT_ROLE_MODEL]
            ).values_list("role", "content")
        )

        Message.objects.create(
            conversation=conversation, role=Constants.ASSISTANT_ROLE_USER, content=user_text
        )

        context = ToolContext(car=conversation.car, owner_id=conversation.owner_id)
        try:
            result = run_chat(history=history, user_text=user_text, context=context)
        except Exception:  # noqa: BLE001 — log the provider/SDK detail, surface a clean 502
            logger.exception("Gemini chat call failed for conversation %s", conversation.id)
            raise CustomValidation(
                "The assistant is unavailable right now. Please try again shortly.",
                field="detail",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        reply = Message.objects.create(
            conversation=conversation,
            role=Constants.ASSISTANT_ROLE_MODEL,
            content=result.text,
            tool_calls=result.tool_calls,
        )
        # Touch updated_at so the conversation floats to the top of the list.
        conversation.save(update_fields=["updated_at"])
        return Response(MessageListSerializer(reply).data, status=status.HTTP_201_CREATED)

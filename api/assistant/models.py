import uuid

from django.conf import settings
from django.db import models

from utils import Constants

from cars.models import Car


class Conversation(models.Model):
    """
    A chat thread between an owner and the AI assistant, scoped to one of the
    owner's cars. Pinning the conversation to a `Car` means every message is
    grounded in a real vehicle we already store (make/model/year/VIN/fuel/
    odometer) — the assistant never has to guess the vehicle context.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations")
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="conversations")

    title = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]

    def __str__(self):
        return self.title or f"Conversation {self.pk}"


class Message(models.Model):
    """
    A single turn in a conversation. `role` mirrors Gemini's role names so the
    persisted history maps 1:1 onto the provider's `contents`. `tool_calls`
    records any tools the assistant invoked to produce a reply — kept for
    transparency (surface "sources" in the UI) and debugging.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")

    role = models.CharField(max_length=10, choices=Constants.ASSISTANT_ROLES)
    content = models.TextField(blank=True)
    tool_calls = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"

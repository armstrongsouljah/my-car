from django.urls import path

from assistant.views import (
    ConversationListCreateView,
    ConversationDetailView,
    MessageListCreateView,
)

urlpatterns = [
    path("conversations/", ConversationListCreateView.as_view(), name="conversation-list-create"),
    path("conversations/<uuid:pk>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path("conversations/<uuid:pk>/messages/", MessageListCreateView.as_view(), name="conversation-messages"),
]

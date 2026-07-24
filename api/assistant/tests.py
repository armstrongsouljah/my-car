from datetime import date
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from accounts.models import User
from cars.models import Car
from services.models import ServiceRecord
from expenses.models import Expense
from utils import Constants

from assistant.gemini import ChatResult
from assistant.models import Conversation, Message
from assistant.tools import ToolContext, execute_tool


@pytest.fixture
def owner(db):
    return User.objects.create_user(email="owner@example.com", password="str0ng-pass-123")


@pytest.fixture
def car(owner):
    return Car.objects.create(owner=owner, make="Toyota", model="Corolla", year=2019, current_odometer_km=40000)


@pytest.fixture
def client(owner):
    api = APIClient()
    api.force_authenticate(owner)
    return api


@pytest.mark.django_db
class TestTools:
    def test_vehicle_details_come_from_the_pinned_car(self, car):
        result = execute_tool("get_vehicle_details", {}, ToolContext(car=car, owner_id=car.owner_id))
        assert result["make"] == "Toyota"
        assert result["current_odometer_km"] == 40000

    def test_service_history_lists_recent_records(self, car):
        ServiceRecord.objects.create(car=car, odometer_km=41000, service_date=date(2026, 1, 1))
        result = execute_tool("get_service_history", {}, ToolContext(car=car, owner_id=car.owner_id))
        assert result["count"] == 1
        assert result["services"][0]["odometer_km"] == 41000

    def test_expense_summary_totals_by_category(self, car):
        Expense.objects.create(car=car, category=Constants.EXPENSE_CATEGORY_FUEL, amount=50)
        Expense.objects.create(car=car, category=Constants.EXPENSE_CATEGORY_FUEL, amount=70)
        result = execute_tool("get_expense_summary", {}, ToolContext(car=car, owner_id=car.owner_id))
        assert result["total"] == "120.00"

    def test_lookup_dtc_known_generic_code(self, car):
        result = execute_tool("lookup_dtc", {"code": "p0420"}, ToolContext(car=car, owner_id=car.owner_id))
        assert result["scope"] == "generic"
        assert "Catalyst" in result["meaning"]

    def test_lookup_dtc_covers_the_full_bundled_generic_set(self, car):
        from assistant.tools import _GENERIC_DTC

        assert len(_GENERIC_DTC) > 100
        result = execute_tool("lookup_dtc", {"code": "U0100"}, ToolContext(car=car, owner_id=car.owner_id))
        assert "ECM" in result["meaning"]

    def test_lookup_dtc_manufacturer_specific_code_is_reported_as_unavailable(self, car):
        result = execute_tool("lookup_dtc", {"code": "P1234"}, ToolContext(car=car, owner_id=car.owner_id))
        assert result["meaning"] is None
        assert "licensed" in result["note"]

    def test_unknown_tool_returns_error(self, car):
        result = execute_tool("nope", {}, ToolContext(car=car, owner_id=car.owner_id))
        assert "error" in result


@pytest.mark.django_db
class TestConversationScoping:
    def test_create_conversation_pins_to_owned_car(self, client, car):
        resp = client.post("/api/v1/assistant/conversations/", {"car": str(car.id)}, format="json")
        assert resp.status_code == 201
        assert resp.data["title"] == "Toyota Corolla"

    def test_cannot_open_conversation_on_someone_elses_car(self, client, db):
        stranger = User.objects.create_user(email="x@example.com", password="str0ng-pass-123")
        other_car = Car.objects.create(owner=stranger, make="Honda", model="Civic")
        resp = client.post("/api/v1/assistant/conversations/", {"car": str(other_car.id)}, format="json")
        assert resp.status_code == 404

    def test_cannot_read_someone_elses_conversation(self, client, db):
        stranger = User.objects.create_user(email="x@example.com", password="str0ng-pass-123")
        their_car = Car.objects.create(owner=stranger, make="Honda", model="Civic")
        convo = Conversation.objects.create(owner=stranger, car=their_car)
        resp = client.get(f"/api/v1/assistant/conversations/{convo.id}/messages/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestChatEndpoint:
    def test_send_message_persists_both_turns(self, client, car):
        convo = Conversation.objects.create(owner=car.owner, car=car)
        fake = ChatResult(text="Your next service is due soon.", tool_calls=[{"name": "get_maintenance_status", "args": {}, "result": {}}])
        with patch("assistant.views.run_chat", return_value=fake) as mock_run:
            resp = client.post(
                f"/api/v1/assistant/conversations/{convo.id}/messages/",
                {"content": "When is my next service?"},
                format="json",
            )
        assert resp.status_code == 201
        assert resp.data["content"] == "Your next service is due soon."
        assert resp.data["role"] == Constants.ASSISTANT_ROLE_MODEL
        mock_run.assert_called_once()
        roles = list(convo.messages.values_list("role", flat=True))
        assert roles == [Constants.ASSISTANT_ROLE_USER, Constants.ASSISTANT_ROLE_MODEL]

    def test_empty_message_is_rejected(self, client, car):
        convo = Conversation.objects.create(owner=car.owner, car=car)
        resp = client.post(
            f"/api/v1/assistant/conversations/{convo.id}/messages/", {"content": "  "}, format="json"
        )
        assert resp.status_code == 400
        assert Message.objects.filter(conversation=convo).count() == 0

    def test_provider_failure_surfaces_as_502_without_orphan_reply(self, client, car):
        convo = Conversation.objects.create(owner=car.owner, car=car)
        with patch("assistant.views.run_chat", side_effect=RuntimeError("boom")):
            resp = client.post(
                f"/api/v1/assistant/conversations/{convo.id}/messages/", {"content": "hi"}, format="json"
            )
        assert resp.status_code == 502
        # The user turn is saved; no assistant reply was persisted.
        assert list(convo.messages.values_list("role", flat=True)) == [Constants.ASSISTANT_ROLE_USER]

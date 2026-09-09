"""Regression tests for the whatsloon-based Rasa connector.

Rasa and Sanic are stubbed because they are runtime-only dependencies;
whatsloon itself is real (installed editable from D:/whatsloon).
"""

import sys
import types


def _install_stubs() -> None:
    if "rasa.core.channels.channel" in sys.modules:
        return
    rasa = types.ModuleType("rasa")
    core = types.ModuleType("rasa.core")
    channels = types.ModuleType("rasa.core.channels")
    channel = types.ModuleType("rasa.core.channels.channel")

    class InputChannel:
        @classmethod
        def name(cls):
            return "whatsapp"

        @classmethod
        def raise_missing_credentials_exception(cls):
            raise ValueError("Missing credentials")

    class OutputChannel:
        pass

    class UserMessage:
        def __init__(self, text, output_channel, sender_id, **kwargs):
            self.text = text
            self.output_channel = output_channel
            self.sender_id = sender_id
            self.kwargs = kwargs

    channel.InputChannel = InputChannel
    channel.OutputChannel = OutputChannel
    channel.UserMessage = UserMessage
    sys.modules["rasa"] = rasa
    sys.modules["rasa.core"] = core
    sys.modules["rasa.core.channels"] = channels
    sys.modules["rasa.core.channels.channel"] = channel

    sanic = types.ModuleType("sanic")
    sanic_request = types.ModuleType("sanic.request")
    sanic_response = types.ModuleType("sanic.response")

    class Blueprint:
        def __init__(self, *args, **kwargs):
            self.routes = []

        def route(self, *args, **kwargs):
            def deco(fn):
                self.routes.append(fn)
                return fn

            return deco

    class _Response:
        @staticmethod
        def json(payload, status=200):
            return (payload, status)

        @staticmethod
        def text(body, status=200):
            return (body, status)

    sanic.Blueprint = Blueprint
    sanic.response = _Response
    sanic_request.Request = object
    sanic_response.HTTPResponse = object
    sys.modules["sanic"] = sanic
    sys.modules["sanic.request"] = sanic_request
    sys.modules["sanic.response"] = sanic_response


_install_stubs()

import pytest
from whatsloon.exceptions import InvalidPayloadError
from whatsloon.webhooks.events import WebhookMessageReceived
from whatsloon.webhooks.parser import parse_envelope
from whatsloon.webhooks.verifier import verify_handshake

import whatsapp


def test_extract_text_body():
    raw = {"type": "text", "text": {"body": "Hello"}}
    assert whatsapp.extract_inbound_text(raw) == "Hello"


def test_extract_empty_text_returns_none():
    assert (
        whatsapp.extract_inbound_text({"type": "text", "text": {"body": "  "}}) is None
    )


def test_extract_button_reply_prefers_id():
    raw = {
        "type": "interactive",
        "interactive": {"button_reply": {"id": "/affirm", "title": "Yes"}},
    }
    assert whatsapp.extract_inbound_text(raw) == "/affirm"


def test_extract_list_reply_id():
    raw = {
        "type": "interactive",
        "interactive": {"list_reply": {"id": "row-1", "title": "One"}},
    }
    assert whatsapp.extract_inbound_text(raw) == "row-1"


def test_extract_media_caption_and_missing():
    assert (
        whatsapp.extract_inbound_text({"type": "image", "image": {"caption": "Look"}})
        == "Look"
    )
    assert whatsapp.extract_inbound_text({"type": "image", "image": {}}) is None
    assert whatsapp.extract_inbound_text({"type": "audio", "audio": {}}) is None


def test_extract_location():
    raw = {"type": "location", "location": {"latitude": 1.5, "longitude": 2.5}}
    assert whatsapp.extract_inbound_text(raw) == "1.5,2.5"


def test_chunk_text_respects_limit():
    chunks = whatsapp.chunk_text("a" * 9000)
    assert len(chunks) == 3
    assert all(len(c) <= whatsapp.MAX_TEXT_CHUNK for c in chunks)


def test_handshake_rejects_wrong_token():
    with pytest.raises(InvalidPayloadError):
        verify_handshake(
            mode="subscribe",
            verify_token_expected="secret",
            verify_token_received="wrong",
            challenge="123",
        )


def test_parse_envelope_fixture_yields_received_event():
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "123"},
                            "contacts": [{"wa_id": "919876543210"}],
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "wamid.1",
                                    "timestamp": "1725000000",
                                    "type": "text",
                                    "text": {"body": "Hi"},
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }
    events = parse_envelope(payload)
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, WebhookMessageReceived)
    assert event.sender == "919876543210"
    assert whatsapp.extract_inbound_text(event.raw) == "Hi"

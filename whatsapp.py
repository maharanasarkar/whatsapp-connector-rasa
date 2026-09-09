import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Text

from rasa.core.channels.channel import InputChannel, OutputChannel, UserMessage
from sanic import Blueprint, response
from sanic.request import Request
from sanic.response import HTTPResponse
from whatsloon.client import WhatsApp
from whatsloon.exceptions import InvalidPayloadError, InvalidSignatureError
from whatsloon.messages.builders import ButtonsBuilder
from whatsloon.webhooks.events import WebhookMessageReceived
from whatsloon.webhooks.parser import parse_envelope
from whatsloon.webhooks.verifier import verify_handshake, verify_signature

logger = logging.getLogger(__name__)

MAX_TEXT_CHUNK = 4096
MAX_BUTTONS = 3
MAX_BUTTON_TITLE = 20


def extract_inbound_text(raw_message: Dict[Text, Any]) -> Optional[Text]:
    """Extract routable text from a raw Meta message object.

    Args:
        raw_message: Single entry of the webhook ``messages`` array.

    Returns:
        Text for the Rasa pipeline, or None when the message carries
        no routable content (e.g. audio without transcription, statuses).
    """
    if not isinstance(raw_message, dict):
        return None
    kind = raw_message.get("type")
    if kind == "text":
        text = raw_message.get("text") or {}
        body = text.get("body")
        return body if isinstance(body, str) and body.strip() else None
    if kind == "interactive":
        interactive = raw_message.get("interactive") or {}
        button_reply = interactive.get("button_reply") or {}
        if button_reply.get("id"):
            return button_reply["id"]
        if button_reply.get("title"):
            return button_reply["title"]
        list_reply = interactive.get("list_reply") or {}
        if list_reply.get("id"):
            return list_reply["id"]
        if list_reply.get("title"):
            return list_reply["title"]
        return None
    if kind in ("image", "video", "document"):
        media = raw_message.get(kind) or {}
        caption = media.get("caption")
        if isinstance(caption, str) and caption.strip():
            return caption
        return None
    if kind == "location":
        location = raw_message.get("location") or {}
        latitude = location.get("latitude")
        longitude = location.get("longitude")
        if latitude is not None and longitude is not None:
            return f"{latitude},{longitude}"
        return None
    return None


def chunk_text(text: Text, limit: int = MAX_TEXT_CHUNK) -> List[Text]:
    """Split long text into Meta-compliant chunks."""
    return [text[i : i + limit] for i in range(0, len(text), limit)] or []


class WhatsAppOutput(OutputChannel):
    """Output channel for WhatsApp Cloud API via whatsloon v3."""

    @classmethod
    def name(cls) -> Text:
        return "whatsapp"

    def __init__(
        self,
        access_token: Optional[Text] = None,
        phone_number_id: Optional[Text] = None,
        graph_api_version: Text = "latest",
        **kwargs: Any,
    ) -> None:
        """Initialize the output channel.

        Args:
            access_token: Meta access token (``auth_token`` accepted as alias).
            phone_number_id: Sender phone number ID.
            graph_api_version: Pinned Graph API version or ``"latest"``.
        """
        token = access_token or kwargs.get("auth_token")
        self.client = WhatsApp(
            access_token=token or "",
            phone_number_id=phone_number_id or "",
            graph_api_version=graph_api_version,
        )

    async def send_text_message(
        self, recipient_id: Text, text: Text, **kwargs: Any
    ) -> None:
        """Send a text message, chunked to the Meta limit."""
        for part in text.strip().split("\n\n"):
            part = part.strip()
            if not part:
                continue
            for chunk in chunk_text(part):
                try:
                    await asyncio.to_thread(
                        self.client.messages.send_text, to=recipient_id, body=chunk
                    )
                except Exception:
                    logger.exception("Failed to send WhatsApp text message")

    async def send_text_with_buttons(
        self,
        recipient_id: Text,
        text: Text,
        buttons: List[Dict[Text, Any]],
        **kwargs: Any,
    ) -> None:
        """Send reply buttons, degrading gracefully past API limits."""
        usable = [b for b in (buttons or []) if b.get("payload")]
        if not usable:
            await self.send_text_message(recipient_id, text, **kwargs)
            return
        builder = ButtonsBuilder(text)
        for button in usable[:MAX_BUTTONS]:
            title = str(button.get("title") or button["payload"])
            if len(title) > MAX_BUTTON_TITLE:
                logger.warning("Truncating button title to 20 chars: %r", title)
                title = title[:MAX_BUTTON_TITLE]
            builder.button(str(button["payload"]), title)
        try:
            await asyncio.to_thread(
                self.client.messages.send_reply_buttons,
                to=recipient_id,
                content=builder.build(),
            )
        except Exception:
            logger.exception("Failed to send WhatsApp reply buttons")
            return
        overflow = usable[MAX_BUTTONS:]
        if overflow:
            fallback = "\n".join(
                f"{i + MAX_BUTTONS + 1}. {b.get('title', b['payload'])}"
                for i, b in enumerate(overflow)
            )
            await self.send_text_message(recipient_id, fallback, **kwargs)

    async def send_image_url(
        self, recipient_id: Text, image: Text, **kwargs: Any
    ) -> None:
        """Send an image by URL."""
        try:
            await asyncio.to_thread(
                self.client.messages.send_image,
                to=recipient_id,
                media_link=image,
                caption=kwargs.get("caption"),
            )
        except Exception:
            logger.exception("Failed to send WhatsApp image")

    async def send_video_url(
        self, recipient_id: Text, video: Text, **kwargs: Any
    ) -> None:
        """Send a video by URL."""
        try:
            await asyncio.to_thread(
                self.client.messages.send_video,
                to=recipient_id,
                media_link=video,
                caption=kwargs.get("caption"),
            )
        except Exception:
            logger.exception("Failed to send WhatsApp video")

    async def send_document_url(
        self, recipient_id: Text, document: Text, **kwargs: Any
    ) -> None:
        """Send a document by URL."""
        try:
            await asyncio.to_thread(
                self.client.messages.send_document,
                to=recipient_id,
                media_link=document,
                filename=kwargs.get("filename"),
                caption=kwargs.get("caption"),
            )
        except Exception:
            logger.exception("Failed to send WhatsApp document")

    async def send_audio_url(
        self, recipient_id: Text, audio: Text, **kwargs: Any
    ) -> None:
        """Send audio by URL."""
        try:
            await asyncio.to_thread(
                self.client.messages.send_audio, to=recipient_id, media_link=audio
            )
        except Exception:
            logger.exception("Failed to send WhatsApp audio")

    async def send_custom_json(
        self, recipient_id: Text, json_message: Dict[Text, Any], **kwargs: Any
    ) -> None:
        """Send template or location payloads from custom JSON."""
        try:
            template = json_message.get("template")
            if template:
                await asyncio.to_thread(
                    self.client.messages.send_template,
                    to=recipient_id,
                    template_name=template["name"],
                    language_code=template.get("language", "en_US"),
                    components=template.get("components"),
                )
                return
            location = json_message.get("location")
            if location:
                await asyncio.to_thread(
                    self.client.messages.send_location,
                    to=recipient_id,
                    latitude=float(location["latitude"]),
                    longitude=float(location["longitude"]),
                    name=location.get("name"),
                    address=location.get("address"),
                )
                return
            logger.warning("Unsupported custom JSON keys: %s", sorted(json_message))
        except Exception:
            logger.exception("Failed to send WhatsApp custom JSON")


class WhatsAppInput(InputChannel):
    """WhatsApp Cloud API input channel via whatsloon v3 webhooks."""

    @classmethod
    def name(cls) -> Text:
        return "whatsapp"

    @classmethod
    def from_credentials(cls, credentials: Optional[Dict[Text, Any]]) -> InputChannel:
        if not credentials:
            cls.raise_missing_credentials_exception()
        assert credentials is not None
        return cls(
            credentials.get("access_token") or credentials.get("auth_token"),
            credentials.get("phone_number_id"),
            credentials.get("verify_token"),
            app_secret=credentials.get("app_secret"),
            graph_api_version=credentials.get("graph_api_version", "latest"),
            debug_mode=credentials.get("debug_mode", True),
        )

    def __init__(
        self,
        access_token: Optional[Text],
        phone_number_id: Optional[Text],
        verify_token: Optional[Text],
        app_secret: Optional[Text] = None,
        graph_api_version: Text = "latest",
        debug_mode: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize the input channel.

        Args:
            access_token: Meta access token (``auth_token`` accepted as alias).
            phone_number_id: Sender phone number ID.
            verify_token: Webhook subscription verify token.
            app_secret: Meta app secret; enables signature verification.
            graph_api_version: Pinned Graph API version or ``"latest"``.
            debug_mode: Re-raise handler errors instead of swallowing them.
        """
        self.access_token = access_token or kwargs.get("auth_token")
        self.phone_number_id = phone_number_id
        self.verify_token = verify_token
        self.app_secret = app_secret
        self.graph_api_version = graph_api_version
        self.debug_mode = debug_mode
        self._output_channel: Optional[OutputChannel] = None

    def blueprint(
        self, on_new_message: Callable[[UserMessage], Awaitable[Any]]
    ) -> Blueprint:
        whatsapp_webhook = Blueprint("whatsapp_webhook", __name__)

        @whatsapp_webhook.route("/", methods=["GET"])
        async def health(_: Request) -> HTTPResponse:
            return response.json({"status": "ok"})

        @whatsapp_webhook.route("/webhook", methods=["GET"])
        async def verify(request: Request) -> HTTPResponse:
            try:
                challenge = verify_handshake(
                    mode=request.args.get("hub.mode"),
                    verify_token_expected=self.verify_token or "",
                    verify_token_received=request.args.get("hub.verify_token"),
                    challenge=request.args.get("hub.challenge"),
                )
            except InvalidPayloadError:
                logger.error("Webhook verification failed")
                return response.text("Invalid verification token", status=403)
            return response.text(challenge)

        @whatsapp_webhook.route("/webhook", methods=["POST"])
        async def message(request: Request) -> HTTPResponse:
            if self.app_secret:
                try:
                    verify_signature(
                        self.app_secret,
                        request.body,
                        request.headers.get("X-Hub-Signature-256"),
                    )
                except InvalidSignatureError:
                    logger.error("Webhook signature verification failed")
                    return response.text("Invalid signature", status=403)
                except Exception:  # noqa: BLE001 - fail closed on any verification error
                    logger.error("Webhook signature verification failed")
                    return response.text("Invalid signature", status=403)
            try:
                events = parse_envelope(request.json or {})
            except (InvalidPayloadError, AttributeError):
                logger.error("Webhook body is not a valid envelope")
                return response.text("", status=204)
            out_channel = self.get_output_channel()
            for event in events:
                if not isinstance(event, WebhookMessageReceived):
                    logger.debug("Ignoring non-message event: %s", type(event).__name__)
                    continue
                text = extract_inbound_text(event.raw or {})
                if not event.sender or text is None:
                    logger.debug("Ignoring message without sender or text")
                    continue
                metadata = {
                    "message_id": event.message_id,
                    "message_type": event.message_type,
                    "timestamp": event.timestamp,
                }
                try:
                    await on_new_message(
                        UserMessage(
                            text,
                            out_channel,
                            event.sender,
                            input_channel=self.name(),
                            metadata=metadata,
                        )
                    )
                except Exception as e:
                    logger.error(f"Exception when trying to handle message.{e}")
                    logger.debug(e, exc_info=True)
                    if self.debug_mode:
                        raise
            return response.text("", status=204)

        return whatsapp_webhook

    def get_output_channel(self) -> OutputChannel:
        if self._output_channel is None:
            self._output_channel = WhatsAppOutput(
                self.access_token,
                self.phone_number_id,
                graph_api_version=self.graph_api_version,
            )
        return self._output_channel

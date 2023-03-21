import logging
from sanic import Blueprint, response
from sanic.request import Request
from sanic.response import HTTPResponse
from typing import Dict, Text, Any, Callable, Awaitable, Optional, TYPE_CHECKING

from rasa.core.channels.channel import InputChannel
from rasa.core.channels.channel import UserMessage, OutputChannel

from heyoo import WhatsApp
from typing import (
    Text,
    List,
    Dict,
    Any,
    Optional,
    Callable,
    Iterable,
    Awaitable,
    NoReturn,
)

logger = logging.getLogger(__name__)


class WhatsAppOutput(WhatsApp, OutputChannel):
    """Output channel for WhatsApp Cloud API"""

    @classmethod
    def name(cls) -> Text:
        return "whatsapp"

    def __init__(
        self,
        auth_token: Optional[Text],
        phone_number_id: Optional[Text],
    ) -> None:
        super().__init__(auth_token, phone_number_id=phone_number_id)

    async def send_text_message(
        self, recipient_id: Text, text: Text, **kwargs: Any
    ) -> None:
        """Sends text message"""

        for message_part in text.strip().split("\n\n"):
            self.send_message(message_part, recipient_id=recipient_id)

    async def send_text_with_buttons(
        self,
        recipient_id: Text,
        text: Text,
        buttons: List[Dict[Text, Any]],
        **kwargs: Any,
    ) -> None:
        """Sends text message with buttons"""
        buttons_list = []
        for button in buttons:
            buttons_list.append({
                        "type": "reply",
                        "reply": {
                            "id": button.get("payload"),
                            "title": button.get("title")
                        }
                    })

        button_dict = {"type": "button", "body": {
                "text": text},
                "action": {
                    "buttons": buttons_list
                }
            }
        self.send_reply_button(button=button_dict, recipient_id=recipient_id)


    async def send_image_url(
        self, recipient_id: Text, image: Text, **kwargs: Any
    ) -> None:
        """Sends an image."""

        self.send_image(image, recipient_id=recipient_id)

    async def send_video_url(
            self, recipient_id: Text, video: Text, **kwargs: Any
    ) -> None:
        """Sends a Video"""
        self.send_video(video, recipient_id=recipient_id)

    async def send_document_url(
            self, recipient_id: Text, document: Text, **kwargs: Any
    ) -> None:
        """Sends a Document"""
        self.send_document(document, recipient_id=recipient_id)

    async def send_audio_url(
            self, recipient_id: Text, audio: Text, **kwargs: Any
    ) -> None:
        """Sends an Audio"""
        self.send_audio(audio, recipient_id=recipient_id)

    async def send_location_url(
            self, recipient_id: Text, location: Text, **kwargs: Any
    ) -> None:
        """Sends the Location"""
        self.send_location(location, recipient_id=recipient_id)

class WhatsAppInput(InputChannel):
    """WhatsApp Cloud API input channel"""

    @classmethod
    def name(cls) -> Text:
        return "whatsapp"

    @classmethod
    def from_credentials(cls, credentials: Optional[Dict[Text, Any]]) -> InputChannel:
        if not credentials:
            cls.raise_missing_credentials_exception()

        return cls(
            credentials.get("auth_token"),
            credentials.get("phone_number_id"),
            credentials.get("verify_token")
        )

    def __init__(
        self,
        auth_token: Optional[Text],
        phone_number_id: Optional[Text],
        verify_token: Optional[Text],
        debug_mode: bool = True,
    ) -> None:
        self.auth_token = auth_token
        self.phone_number_id = phone_number_id
        self.verify_token = verify_token
        self.debug_mode = debug_mode
        self.client = WhatsApp(self.auth_token, phone_number_id=self.phone_number_id)
    def get_message(self, data):
        message_type = self.client.get_message_type(data)
        if message_type == "interactive":
            response = self.client.get_interactive_response(data)
            
            if response.get("type") == "button_reply":
                return response.get("button_reply").get("id")
        return self.client.get_message(data)
    
    def blueprint(
        self, on_new_message: Callable[[UserMessage], Awaitable[Any]]
    ) -> Blueprint:
        whatsapp_webhook = Blueprint("whatsapp_webhook", __name__)

        @whatsapp_webhook.route("/", methods=["GET"])
        async def health(_: Request) -> HTTPResponse:
            return response.json({"status": "ok"})

        @whatsapp_webhook.route("/webhook", methods=["GET"])
        async def verify_token(request: Request) -> HTTPResponse:
            print(request.args.get("hub.verify_token"))
            print(self.verify_token)
            print(request.args.get("hub.verify_token") == self.verify_token)
            if request.args.get("hub.verify_token") == self.verify_token:
               return response.text(request.args.get("hub.challenge"))
            print("Webhook Verification failed")
            logging.error("Webhook Verification failed")
            return "Invalid verification token"

        @whatsapp_webhook.route("/webhook", methods=["POST"])
        async def message(request: Request) -> HTTPResponse:
            sender = self.client.get_mobile(request.json)
            #logger.debug(request.json)
            #text = self.client.get_message(request.json) #TODO This will not work for image caption and buttons
            
            text = self.get_message(request.json)
            logger.debug(text)
            
            out_channel = self.get_output_channel()
            if sender is not None and message is not None:
                metadata = self.get_metadata(request)
                try:
                    await on_new_message(
                        UserMessage(
                            text,
                            out_channel,
                            sender,
                            input_channel=self.name(),
                            metadata=metadata,
                        )
                    )
                except Exception as e:
                    logger.error(f"Exception when trying to handle message.{e}")
                    logger.debug(e, exc_info=True)
                    if self.debug_mode:
                        raise
                    pass
            else:
                logger.debug("Invalid message")

            return response.text("", status=204)

        return whatsapp_webhook

    def get_output_channel(self) -> OutputChannel:
        return WhatsAppOutput(self.auth_token, self.phone_number_id)

import logging
from sanic import Blueprint, Request, response
from sanic.request import Request
from sanic.response import HTTPResponse

from rasa.core.channels.channel import InputChannel, OutputChannel, UserMessage

from whatsloon import WhatsAppCloudAPIClient

from typing import (
    Text,
    List,
    Dict,
    Any,
    Optional,
    Callable,
    Awaitable,
    NoReturn,
)

logger = logging.getLogger(__name__)

class WhatsAppOutput(WhatsAppCloudAPIClient, OutputChannel):
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
        self, text: Text, **kwargs: Any
    ) -> None:
        """Sends text message"""
        self.async_send_text_message(message_text=text, preview_url=True)
        
    async def send_text_with_buttons(
        self,
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
                    "id": button["payload"],
                    "title": button["title"]
                }
            })
        
        self.async_send_reply_buttons_message(
            body_text=text,
            buttons=buttons_list
        )
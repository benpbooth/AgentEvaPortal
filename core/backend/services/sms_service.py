"""
SMS Service - Handles Twilio SMS integration
"""
import logging
from typing import Optional
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

logger = logging.getLogger(__name__)


class SMSService:
    """Service for sending and receiving SMS via Twilio."""

    def __init__(self, account_sid: str, auth_token: str, phone_number: str):
        """
        Initialize SMS service with Twilio credentials.

        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            phone_number: Twilio phone number (from)
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.phone_number = phone_number
        self.client = Client(account_sid, auth_token)

    def send_sms(self, to: str, message: str) -> Optional[str]:
        """
        Send an SMS message.

        Args:
            to: Recipient phone number (e.g., "+15555555555")
            message: Message text to send

        Returns:
            Message SID if successful, None otherwise
        """
        try:
            twilio_message = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to
            )

            logger.info(f"SMS sent to {to}: {twilio_message.sid}")
            return twilio_message.sid

        except Exception as e:
            logger.error(f"Failed to send SMS to {to}: {str(e)}")
            return None

    @staticmethod
    def create_twiml_response(message: str) -> str:
        """
        Create TwiML response for Twilio webhook.

        Args:
            message: Message text to send in response

        Returns:
            TwiML XML string
        """
        response = MessagingResponse()
        response.message(message)
        return str(response)

    @staticmethod
    def validate_webhook_signature(
        url: str,
        params: dict,
        signature: str,
        auth_token: str
    ) -> bool:
        """
        Validate Twilio webhook signature for security.

        Args:
            url: Full webhook URL
            params: Request POST parameters
            signature: X-Twilio-Signature header value
            auth_token: Twilio auth token

        Returns:
            True if signature is valid, False otherwise
        """
        from twilio.request_validator import RequestValidator

        validator = RequestValidator(auth_token)
        return validator.validate(url, params, signature)

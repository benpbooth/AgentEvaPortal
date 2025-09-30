"""Webhook endpoints for external integrations (Twilio, Vapi, SendGrid, etc.)."""

import hashlib
import hmac
import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.backend.services.chat_service import ChatService
from core.database.base import get_db
from core.database.models import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ============================================================================
# Request/Response Models
# ============================================================================

class TwilioSMSWebhook(BaseModel):
    """Twilio SMS webhook payload."""
    From: str = Field(..., description="Sender phone number")
    To: str = Field(..., description="Recipient phone number")
    Body: str = Field(..., description="Message body")
    MessageSid: str = Field(..., description="Twilio message ID")
    AccountSid: str = Field(..., description="Twilio account ID")


class TwilioVoiceWebhook(BaseModel):
    """Twilio Voice webhook payload."""
    CallSid: str = Field(..., description="Twilio call ID")
    From: str = Field(..., description="Caller phone number")
    To: str = Field(..., description="Called phone number")
    CallStatus: str = Field(..., description="Call status")
    Digits: Optional[str] = Field(None, description="DTMF digits pressed")
    SpeechResult: Optional[str] = Field(None, description="Transcribed speech")


class VapiWebhook(BaseModel):
    """Vapi voice assistant webhook payload."""
    message_type: str = Field(..., description="Type of message (call-start, transcript, call-end)")
    call_id: str = Field(..., description="Vapi call ID")
    transcript: Optional[str] = Field(None, description="User speech transcript")
    phone_number: Optional[str] = Field(None, description="Caller phone number")
    metadata: Optional[dict] = Field(default_factory=dict)


class SendGridWebhook(BaseModel):
    """SendGrid inbound email webhook payload."""
    from_email: str = Field(..., alias="from")
    to: str = Field(..., description="Recipient email")
    subject: str = Field(..., description="Email subject")
    text: str = Field(..., description="Email body (plain text)")
    html: Optional[str] = Field(None, description="Email body (HTML)")


# ============================================================================
# Security Helper Functions
# ============================================================================

def verify_twilio_signature(
    url: str,
    params: dict,
    signature: str,
    auth_token: str
) -> bool:
    """
    Verify Twilio webhook signature.

    Args:
        url: Full URL of webhook endpoint
        params: POST parameters from Twilio
        signature: X-Twilio-Signature header value
        auth_token: Twilio auth token from settings

    Returns:
        True if signature is valid
    """
    # Create signature string
    sig_string = url + "".join([f"{k}{v}" for k, v in sorted(params.items())])

    # Calculate expected signature
    expected = hmac.new(
        auth_token.encode('utf-8'),
        sig_string.encode('utf-8'),
        hashlib.sha1
    ).digest()

    # Compare with provided signature
    return hmac.compare_digest(
        signature.encode('utf-8'),
        expected.hex().encode('utf-8')
    )


async def get_tenant_by_phone(phone: str, db: Session) -> Optional[Tenant]:
    """
    Get tenant by phone number mapping.

    For production, you'd have a phone_numbers table mapping
    phone numbers to tenants. For now, we'll use a simple lookup.
    """
    # TODO: Implement phone number -> tenant mapping
    # For demo, just return the demo tenant
    return db.query(Tenant).filter(Tenant.slug == "demo").first()


async def get_tenant_by_email(email: str, db: Session) -> Optional[Tenant]:
    """Get tenant by email domain mapping."""
    # TODO: Implement email domain -> tenant mapping
    return db.query(Tenant).filter(Tenant.slug == "demo").first()


# ============================================================================
# Twilio SMS Webhook
# ============================================================================

@router.post(
    "/twilio/sms",
    summary="Twilio SMS webhook",
    description="Receives incoming SMS messages from Twilio"
)
async def twilio_sms_webhook(
    request: Request,
    x_twilio_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Handle incoming SMS from Twilio.

    Expected format: application/x-www-form-urlencoded
    """
    try:
        # Parse form data
        form_data = await request.form()
        data = dict(form_data)

        logger.info(f"Received Twilio SMS webhook: {data.get('From')} -> {data.get('To')}")

        # Verify signature (in production)
        # TODO: Enable signature verification
        # if not verify_twilio_signature(str(request.url), data, x_twilio_signature, twilio_auth_token):
        #     raise HTTPException(status_code=401, detail="Invalid signature")

        # Get tenant from phone number
        tenant = await get_tenant_by_phone(data.get('To'), db)
        if not tenant:
            logger.warning(f"No tenant found for phone: {data.get('To')}")
            return {"message": "Phone number not configured"}

        # Process message with ChatService
        chat_service = ChatService(tenant.slug, db)

        # Use phone number as session ID
        session_id = f"sms_{data.get('From')}"

        result = await chat_service.process_message(
            message=data.get('Body', ''),
            session_id=session_id,
            channel='sms'
        )

        # Return TwiML response
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{result['response']}</Message>
</Response>"""

        return Response(content=twiml, media_type="application/xml")

    except Exception as e:
        logger.error(f"Error processing Twilio SMS webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing SMS")


# ============================================================================
# Twilio Voice Webhook
# ============================================================================

@router.post(
    "/twilio/voice",
    summary="Twilio Voice webhook",
    description="Receives incoming voice calls from Twilio"
)
async def twilio_voice_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle incoming voice call from Twilio.

    Returns TwiML to gather speech input.
    """
    try:
        form_data = await request.form()
        data = dict(form_data)

        logger.info(f"Received Twilio Voice webhook: {data.get('CallStatus')}")

        # Get tenant
        tenant = await get_tenant_by_phone(data.get('To'), db)
        if not tenant:
            return Response(content="""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>This number is not configured. Goodbye.</Say>
    <Hangup/>
</Response>""", media_type="application/xml")

        # If speech result available, process it
        if data.get('SpeechResult'):
            chat_service = ChatService(tenant.slug, db)
            session_id = f"voice_{data.get('CallSid')}"

            result = await chat_service.process_message(
                message=data.get('SpeechResult'),
                session_id=session_id,
                channel='voice'
            )

            # Return TwiML with AI response
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>{result['response']}</Say>
    <Gather input="speech" action="/webhooks/twilio/voice" method="POST" timeout="3">
        <Say>How else can I help you?</Say>
    </Gather>
</Response>"""

        else:
            # Initial greeting
            twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="/webhooks/twilio/voice" method="POST" timeout="3">
        <Say>Hello! I'm your AI assistant. How can I help you today?</Say>
    </Gather>
</Response>"""

        return Response(content=twiml, media_type="application/xml")

    except Exception as e:
        logger.error(f"Error processing Twilio Voice webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing call")


# ============================================================================
# Vapi Voice Webhook
# ============================================================================

@router.post(
    "/vapi/{tenant_id}",
    summary="Vapi voice assistant webhook",
    description="Receives events from Vapi voice assistant"
)
async def vapi_webhook(
    tenant_id: str,
    webhook: VapiWebhook,
    db: Session = Depends(get_db)
):
    """
    Handle Vapi voice assistant events.

    Vapi sends various events during a call:
    - call-start
    - transcript (user speech)
    - call-end
    """
    try:
        logger.info(f"Received Vapi webhook: {webhook.message_type} for tenant {tenant_id}")

        # Only process transcript events
        if webhook.message_type != "transcript" or not webhook.transcript:
            return {"status": "ok"}

        # Process with ChatService
        chat_service = ChatService(tenant_id, db)
        session_id = f"vapi_{webhook.call_id}"

        result = await chat_service.process_message(
            message=webhook.transcript,
            session_id=session_id,
            channel='voice'
        )

        # Return response for Vapi to speak
        return {
            "response": result['response'],
            "end_call": result.get('escalate', False)
        }

    except Exception as e:
        logger.error(f"Error processing Vapi webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing voice call")


# ============================================================================
# SendGrid Email Webhook
# ============================================================================

@router.post(
    "/sendgrid/inbound",
    summary="SendGrid inbound email webhook",
    description="Receives incoming emails via SendGrid"
)
async def sendgrid_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle incoming email from SendGrid.

    SendGrid sends emails as multipart/form-data.
    """
    try:
        form_data = await request.form()

        from_email = form_data.get('from')
        to_email = form_data.get('to')
        subject = form_data.get('subject', '')
        text = form_data.get('text', '')

        logger.info(f"Received email from {from_email} to {to_email}")

        # Get tenant from email domain
        tenant = await get_tenant_by_email(to_email, db)
        if not tenant:
            logger.warning(f"No tenant found for email: {to_email}")
            return {"message": "Email not configured"}

        # Process with ChatService
        chat_service = ChatService(tenant.slug, db)
        session_id = f"email_{from_email}"

        result = await chat_service.process_message(
            message=f"Subject: {subject}\n\n{text}",
            session_id=session_id,
            channel='email'
        )

        # TODO: Send email response via SendGrid API
        logger.info(f"Email response generated: {result['response'][:100]}...")

        return {"message": "Email processed", "response": result['response']}

    except Exception as e:
        logger.error(f"Error processing SendGrid webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing email")


# ============================================================================
# Generic Webhook for Testing
# ============================================================================

@router.post(
    "/test/{tenant_id}",
    summary="Test webhook endpoint",
    description="Generic webhook for testing integrations"
)
async def test_webhook(
    tenant_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Test webhook that accepts any JSON payload."""
    try:
        body = await request.json()
        logger.info(f"Test webhook received for {tenant_id}: {body}")

        message = body.get('message', body.get('text', ''))
        if not message:
            return {"error": "No message field found"}

        chat_service = ChatService(tenant_id, db)
        session_id = body.get('session_id', 'test_session')

        result = await chat_service.process_message(
            message=message,
            session_id=session_id,
            channel='webhook'
        )

        return {
            "status": "success",
            "response": result['response'],
            "session_id": result['session_id']
        }

    except Exception as e:
        logger.error(f"Error in test webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Import Response for TwiML
from fastapi.responses import Response
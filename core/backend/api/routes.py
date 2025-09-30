"""API routes for tenant-specific operations."""

import logging
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.backend.services.chat_service import ChatService
from core.backend.services.retrieval_service import RetrievalService
from core.backend.services.database_service import DatabaseService
from core.backend.utils.security import verify_api_key, hash_api_key
from core.database.base import get_db
from core.database.models import Tenant, KnowledgeDoc

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class ChatMessage(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request payload."""

    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    context: Optional[Dict] = Field(default_factory=dict, description="Additional context")


class ChatResponse(BaseModel):
    """Chat response payload."""

    message: str = Field(..., description="AI assistant response")
    session_id: str = Field(..., description="Session ID")
    conversation_id: UUID = Field(..., description="Conversation UUID")
    confidence: Optional[float] = Field(None, description="Response confidence score")
    suggested_actions: Optional[List[str]] = Field(default_factory=list, description="Suggested follow-up actions")


class TenantConfigResponse(BaseModel):
    """Tenant configuration response."""

    slug: str
    name: str
    branding: Dict
    features: Dict
    business_info: Dict


class AnalyticsResponse(BaseModel):
    """Analytics response."""

    total_conversations: int
    resolved_conversations: int
    escalated_conversations: int
    avg_response_time_ms: float
    avg_csat_score: Optional[float]
    date_range: Dict[str, str]


class KnowledgeDocRequest(BaseModel):
    """Knowledge document upload request."""

    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Document content")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Additional metadata (category, tags, etc.)")


class KnowledgeDocResponse(BaseModel):
    """Knowledge document response."""

    id: UUID = Field(..., description="Document UUID")
    title: str
    content_preview: str = Field(..., description="First 200 characters of content")
    metadata: Dict
    created_at: str


class KnowledgeDocListResponse(BaseModel):
    """Knowledge document list response."""

    documents: List[KnowledgeDocResponse]
    total: int


class WidgetConfigResponse(BaseModel):
    """Widget configuration response for embedding."""

    branding: Dict = Field(..., description="Branding configuration (colors, logo, etc.)")
    features: Dict = Field(default_factory=dict, description="Enabled features")


# Dependency: Verify API Key and Get Tenant
async def verify_api_key_and_get_tenant(
    tenant_id: str,
    x_api_key: Optional[str] = Header(None, description="Tenant API key"),
    db: Session = Depends(get_db)
) -> Tenant:
    """
    Verify tenant API key and return tenant object.

    Args:
        tenant_id: Tenant slug
        x_api_key: API key from header
        db: Database session

    Returns:
        Tenant object

    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Get tenant by slug
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_id).first()

    if not tenant:
        logger.warning(f"Tenant not found: {tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key or tenant not found",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Verify API key - support both hashed and plaintext for migration
    key_valid = False

    if tenant.api_key_hash:
        # Use secure hash comparison if available
        key_valid = verify_api_key(x_api_key, tenant.api_key_hash)
    elif tenant.api_key == x_api_key:
        # Fallback to plaintext comparison for backwards compatibility
        key_valid = True
        # Optionally: Auto-migrate to hashed key
        # tenant.api_key_hash = hash_api_key(x_api_key)
        # db.commit()

    if not key_valid:
        logger.warning(f"Invalid API key for tenant: {tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key or tenant not found",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    logger.info(f"Authenticated API request for tenant: {tenant_id}")
    return tenant


@router.post(
    "/{tenant_id}/chat",
    response_model=ChatResponse,
    tags=["Chat"],
    summary="Send chat message",
    description="Send a message to the AI assistant for a specific tenant",
)
async def chat(
    tenant_id: str,
    request: ChatRequest,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> ChatResponse:
    """
    Handle chat message from user.

    Args:
        tenant_id: Tenant identifier (slug)
        request: Chat request with message and context
        x_api_key: Tenant API key for authentication
        db: Database session

    Returns:
        ChatResponse with AI assistant message
    """
    # Validate API key and get tenant
    tenant = await verify_api_key_and_get_tenant(tenant_id, x_api_key, db)

    logger.info(f"Chat request for tenant {tenant_id}: {request.message[:50]}...")

    try:
        # Initialize ChatService
        chat_service = ChatService(tenant_id, db)

        # Generate session ID if not provided
        session_id = request.session_id or str(uuid4())

        # Process message
        result = await chat_service.process_message(
            message=request.message,
            session_id=session_id,
            channel="chat"
        )

        # Return response
        return ChatResponse(
            message=result["response"],
            session_id=result["session_id"],
            conversation_id=UUID(result["conversation_id"]),
            confidence=result["confidence"],
            suggested_actions=["Talk to human agent"] if result["escalate"] else []
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your message. Please try again."
        )


@router.get(
    "/{tenant_id}/config",
    response_model=TenantConfigResponse,
    tags=["Configuration"],
    summary="Get tenant configuration",
    description="Retrieve public configuration for a tenant (branding, features, etc.)",
)
async def get_tenant_config(
    tenant_id: str,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> TenantConfigResponse:
    """
    Get tenant configuration.

    Args:
        tenant_id: Tenant identifier (slug)
        x_api_key: Tenant API key for authentication
        db: Database session

    Returns:
        TenantConfigResponse with branding and feature configuration
    """
    # Validate API key
    tenant = await verify_api_key_and_get_tenant(tenant_id, x_api_key, db)

    logger.info(f"Config request for tenant: {tenant_id}")

    try:
        # Get configuration from database
        config = tenant.config or {}

        return TenantConfigResponse(
            slug=tenant_id,
            name=tenant.name,
            branding=config.get('branding', {}),
            features=config.get('channels', {}),
            business_info=config.get('business_info', {}),
        )

    except Exception as e:
        logger.error(f"Error loading config for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error loading tenant configuration"
        )


@router.get(
    "/{tenant_id}/analytics",
    response_model=AnalyticsResponse,
    tags=["Analytics"],
    summary="Get analytics data",
    description="Retrieve analytics and metrics for a tenant",
)
async def get_analytics(
    tenant_id: str,
    x_api_key: Optional[str] = Header(None),
    days: int = 30,
) -> AnalyticsResponse:
    """
    Get analytics data for tenant.

    Args:
        tenant_id: Tenant identifier (slug)
        x_api_key: Tenant API key for authentication
        days: Number of days to include in analytics (default: 30)

    Returns:
        AnalyticsResponse with metrics
    """
    await verify_api_key(tenant_id, x_api_key)

    # TODO: Query analytics from database
    logger.info(f"Analytics request for tenant {tenant_id} (last {days} days)")

    # Placeholder response
    return AnalyticsResponse(
        total_conversations=156,
        resolved_conversations=142,
        escalated_conversations=8,
        avg_response_time_ms=1250.5,
        avg_csat_score=4.6,
        date_range={"start": "2025-08-30", "end": "2025-09-29"},
    )


@router.post(
    "/{tenant_id}/knowledge",
    response_model=KnowledgeDocResponse,
    tags=["Knowledge Base"],
    summary="Upload knowledge document",
    description="Upload a document to the knowledge base for RAG",
)
async def upload_knowledge_doc(
    tenant_id: str,
    request: KnowledgeDocRequest,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> KnowledgeDocResponse:
    """
    Upload a document to the knowledge base.

    Args:
        tenant_id: Tenant identifier (slug)
        request: Document content and metadata
        x_api_key: Tenant API key for authentication
        db: Database session

    Returns:
        KnowledgeDocResponse with document details
    """
    tenant = await verify_api_key_and_get_tenant(tenant_id, x_api_key, db)

    logger.info(f"Knowledge doc upload for tenant {tenant_id}: {request.title}")

    try:
        from datetime import datetime
        from uuid import uuid4

        # 1. Save to database
        doc_id = uuid4()
        knowledge_doc = KnowledgeDoc(
            id=doc_id,
            tenant_id=tenant.id,
            title=request.title,
            content=request.content,
            extra_data=request.metadata or {},
            vector_id=str(doc_id),  # Use doc UUID as vector ID
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(knowledge_doc)
        db.commit()
        db.refresh(knowledge_doc)

        # 2. Index in Pinecone
        retrieval_service = RetrievalService(tenant_id)
        success = await retrieval_service.index_document(
            document_id=str(doc_id),
            title=request.title,
            content=request.content,
            metadata=request.metadata or {}
        )

        if not success:
            logger.warning(f"Failed to index document in Pinecone: {doc_id}")

        return KnowledgeDocResponse(
            id=knowledge_doc.id,
            title=knowledge_doc.title,
            content_preview=knowledge_doc.content[:200],
            metadata=knowledge_doc.extra_data,
            created_at=knowledge_doc.created_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Error uploading knowledge doc: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading document"
        )


@router.get(
    "/{tenant_id}/knowledge",
    response_model=KnowledgeDocListResponse,
    tags=["Knowledge Base"],
    summary="List knowledge documents",
    description="Get all knowledge base documents for a tenant",
)
async def list_knowledge_docs(
    tenant_id: str,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> KnowledgeDocListResponse:
    """
    List all knowledge base documents for a tenant.

    Args:
        tenant_id: Tenant identifier (slug)
        x_api_key: Tenant API key for authentication
        db: Database session

    Returns:
        KnowledgeDocListResponse with list of documents
    """
    tenant = await verify_api_key_and_get_tenant(tenant_id, x_api_key, db)

    logger.info(f"List knowledge docs for tenant: {tenant_id}")

    try:
        docs = db.query(KnowledgeDoc).filter(
            KnowledgeDoc.tenant_id == tenant.id
        ).order_by(KnowledgeDoc.created_at.desc()).all()

        return KnowledgeDocListResponse(
            documents=[
                KnowledgeDocResponse(
                    id=doc.id,
                    title=doc.title,
                    content_preview=doc.content[:200],
                    metadata=doc.extra_data,
                    created_at=doc.created_at.isoformat()
                )
                for doc in docs
            ],
            total=len(docs)
        )

    except Exception as e:
        logger.error(f"Error listing knowledge docs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving documents"
        )


@router.delete(
    "/{tenant_id}/knowledge/{doc_id}",
    tags=["Knowledge Base"],
    summary="Delete knowledge document",
    description="Delete a document from the knowledge base",
)
async def delete_knowledge_doc(
    tenant_id: str,
    doc_id: UUID,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Delete a knowledge base document.

    Args:
        tenant_id: Tenant identifier (slug)
        doc_id: Document UUID to delete
        x_api_key: Tenant API key for authentication
        db: Database session

    Returns:
        Success message
    """
    tenant = await verify_api_key_and_get_tenant(tenant_id, x_api_key, db)

    logger.info(f"Delete knowledge doc for tenant {tenant_id}: {doc_id}")

    try:
        # 1. Find document
        doc = db.query(KnowledgeDoc).filter(
            KnowledgeDoc.id == doc_id,
            KnowledgeDoc.tenant_id == tenant.id  # CRITICAL: Tenant isolation
        ).first()

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # 2. Delete from Pinecone
        retrieval_service = RetrievalService(tenant_id)
        await retrieval_service.delete_document(str(doc_id))

        # 3. Delete from database
        db.delete(doc)
        db.commit()

        return {"message": "Document deleted successfully", "id": str(doc_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting knowledge doc: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting document"
        )


# ============================================================================
# Widget Configuration Endpoint
# ============================================================================

@router.get(
    "/{tenant_id}/widget/config",
    response_model=WidgetConfigResponse,
    tags=["Widget"],
    summary="Get widget configuration",
    description="Get branding and configuration for embeddable widget"
)
async def get_widget_config(
    tenant_id: str,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> WidgetConfigResponse:
    """
    Get widget configuration including branding.

    This endpoint is called by the widget JavaScript to fetch
    tenant-specific branding and settings.

    Args:
        tenant_id: Tenant identifier (slug)
        x_api_key: Tenant API key for authentication
        db: Database session

    Returns:
        WidgetConfigResponse with branding and features
    """
    tenant = await verify_api_key_and_get_tenant(tenant_id, x_api_key, db)

    logger.info(f"Widget config request for tenant: {tenant_id}")

    # Extract branding from tenant config
    config = tenant.config or {}
    branding = config.get('branding', {
        'primary_color': '#667eea',
        'secondary_color': '#764ba2',
        'company_name': tenant.name,
        'welcome_message': 'Hi! How can we help you today?',
        'logo_url': '',
        'widget_position': 'bottom-right'
    })

    features = config.get('channels', {
        'web': {'enabled': True}
    })

    return WidgetConfigResponse(
        branding=branding,
        features=features
    )


# ============================================================================
# Dashboard Endpoints (Internal Use)
# ============================================================================

@router.get(
    "/{tenant_id}/dashboard/conversations",
    tags=["Dashboard"],
    summary="List conversations for dashboard",
    description="Get all conversations with pagination and filtering"
)
async def list_conversations(
    tenant_id: str,
    x_api_key: Optional[str] = Header(None),
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List conversations for agent dashboard.

    Args:
        tenant_id: Tenant identifier
        x_api_key: API key for authentication
        status: Filter by status (active, escalated, resolved)
        limit: Number of conversations to return
        offset: Pagination offset
        db: Database session

    Returns:
        List of conversations with message counts
    """
    from core.database.models import Conversation, Message
    from sqlalchemy import func, desc

    tenant = await verify_api_key_and_get_tenant(tenant_id, x_api_key, db)

    logger.info(f"Dashboard conversations list for tenant: {tenant_id}")

    # Build query
    query = db.query(
        Conversation,
        func.count(Message.id).label('message_count')
    ).outerjoin(
        Message, Message.conversation_id == Conversation.id
    ).filter(
        Conversation.tenant_id == tenant.id
    ).group_by(Conversation.id)

    # Apply status filter
    if status:
        from core.database.models import ResolutionStatus
        if status == "escalated":
            query = query.filter(Conversation.escalated == True)
        elif status == "resolved":
            query = query.filter(Conversation.resolution_status == ResolutionStatus.RESOLVED)
        elif status == "active":
            query = query.filter(Conversation.resolution_status == ResolutionStatus.PENDING)

    # Order and paginate
    query = query.order_by(desc(Conversation.started_at))
    conversations = query.offset(offset).limit(limit).all()

    # Format response
    return {
        "conversations": [
            {
                "id": str(conv.id),
                "session_id": conv.session_id,
                "channel": conv.channel,
                "status": conv.resolution_status.value if conv.resolution_status else "unknown",
                "escalated": conv.escalated,
                "message_count": count,
                "started_at": conv.started_at.isoformat(),
                "ended_at": conv.ended_at.isoformat() if conv.ended_at else None
            }
            for conv, count in conversations
        ],
        "total": query.count(),
        "limit": limit,
        "offset": offset
    }


@router.get(
    "/{tenant_id}/dashboard/conversations/{conversation_id}",
    tags=["Dashboard"],
    summary="Get conversation details",
    description="Get full conversation with all messages"
)
async def get_conversation_detail(
    tenant_id: str,
    conversation_id: UUID,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get detailed conversation with all messages.

    Args:
        tenant_id: Tenant identifier
        conversation_id: Conversation UUID
        x_api_key: API key
        db: Database session

    Returns:
        Conversation with full message history
    """
    from core.database.models import Conversation, Message

    tenant = await verify_api_key_and_get_tenant(tenant_id, x_api_key, db)

    # Get conversation
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.tenant_id == tenant.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Get messages
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()

    return {
        "id": str(conversation.id),
        "session_id": conversation.session_id,
        "channel": conversation.channel,
        "status": conversation.resolution_status.value if conversation.resolution_status else "unknown",
        "escalated": conversation.escalated,
        "started_at": conversation.started_at.isoformat(),
        "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
        "messages": [
            {
                "id": str(msg.id),
                "role": msg.role.value,
                "content": msg.content,
                "metadata": msg.extra_data or {},
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]
    }


@router.get(
    "/{tenant_id}/dashboard/stats",
    tags=["Dashboard"],
    summary="Get dashboard statistics",
    description="Get summary stats for the dashboard"
)
async def get_dashboard_stats(
    tenant_id: str,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics.

    Args:
        tenant_id: Tenant identifier
        x_api_key: API key
        db: Database session

    Returns:
        Summary statistics
    """
    from core.database.models import Conversation, Message, ResolutionStatus
    from sqlalchemy import func
    from datetime import datetime, timedelta

    tenant = await verify_api_key_and_get_tenant(tenant_id, x_api_key, db)

    # Total conversations
    total_conversations = db.query(func.count(Conversation.id)).filter(
        Conversation.tenant_id == tenant.id
    ).scalar()

    # Escalated conversations
    escalated_count = db.query(func.count(Conversation.id)).filter(
        Conversation.tenant_id == tenant.id,
        Conversation.escalated == True
    ).scalar()

    # Active conversations
    active_count = db.query(func.count(Conversation.id)).filter(
        Conversation.tenant_id == tenant.id,
        Conversation.resolution_status == ResolutionStatus.PENDING
    ).scalar()

    # Resolved conversations
    resolved_count = db.query(func.count(Conversation.id)).filter(
        Conversation.tenant_id == tenant.id,
        Conversation.resolution_status == ResolutionStatus.RESOLVED
    ).scalar()

    # Total messages
    total_messages = db.query(func.count(Message.id)).filter(
        Message.tenant_id == tenant.id
    ).scalar()

    # Conversations today
    today = datetime.utcnow().date()
    today_count = db.query(func.count(Conversation.id)).filter(
        Conversation.tenant_id == tenant.id,
        func.date(Conversation.started_at) == today
    ).scalar()

    return {
        "total_conversations": total_conversations or 0,
        "active_conversations": active_count or 0,
        "escalated_conversations": escalated_count or 0,
        "resolved_conversations": resolved_count or 0,
        "total_messages": total_messages or 0,
        "conversations_today": today_count or 0,
        "escalation_rate": round((escalated_count / total_conversations * 100) if total_conversations > 0 else 0, 1)
    }


@router.post(
    "/{tenant_id}/sms/webhook",
    tags=["SMS"],
    summary="Twilio SMS webhook",
    description="Receive incoming SMS messages from Twilio"
)
async def sms_webhook(
    tenant_id: str,
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Twilio webhook endpoint for incoming SMS messages.

    Args:
        tenant_id: Tenant identifier
        From: Sender phone number
        To: Recipient phone number (your Twilio number)
        Body: SMS message body
        MessageSid: Twilio message SID
        db: Database session

    Returns:
        TwiML response
    """
    from fastapi import Form, Response
    from core.backend.services.sms_service import SMSService

    logger.info(f"Received SMS from {From} to {To}: {Body}")

    try:
        # Get tenant
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_id).first()
        if not tenant:
            logger.error(f"Tenant {tenant_id} not found")
            return Response(content=SMSService.create_twiml_response("Service unavailable"), media_type="application/xml")

        # Get or create conversation using phone number as session ID
        from core.database.models import Conversation, Message, MessageRole
        conversation = db.query(Conversation).filter(
            Conversation.tenant_id == tenant.id,
            Conversation.session_id == From,
            Conversation.channel == "sms"
        ).first()

        if not conversation:
            conversation = Conversation(
                id=uuid4(),
                tenant_id=tenant.id,
                session_id=From,
                channel="sms"
            )
            db.add(conversation)
            db.commit()
            logger.info(f"Created new SMS conversation for {From}")

        # Save user message
        user_message = Message(
            id=uuid4(),
            conversation_id=conversation.id,
            tenant_id=tenant.id,
            role=MessageRole.USER,
            content=Body,
            extra_data={"channel": "sms", "message_sid": MessageSid, "from": From, "to": To}
        )
        db.add(user_message)
        db.commit()

        # Generate AI response
        chat_service = ChatService(tenant_id, db)
        ai_response = await chat_service.generate_response(Body, From)

        # Save assistant message
        assistant_message = Message(
            id=uuid4(),
            conversation_id=conversation.id,
            tenant_id=tenant.id,
            role=MessageRole.ASSISTANT,
            content=ai_response["message"],
            extra_data={
                "channel": "sms",
                "confidence": ai_response.get("confidence", 0),
                "escalation_triggered": ai_response.get("escalation_triggered", False),
                "documents_used": ai_response.get("documents_used", 0)
            }
        )
        db.add(assistant_message)

        # Update conversation escalation status
        if ai_response.get("escalation_triggered"):
            conversation.escalated = True

        db.commit()

        logger.info(f"SMS response generated for {From}")

        # Return TwiML response
        return Response(
            content=SMSService.create_twiml_response(ai_response["message"]),
            media_type="application/xml"
        )

    except Exception as e:
        logger.error(f"Error processing SMS webhook: {str(e)}")
        db.rollback()
        return Response(
            content=SMSService.create_twiml_response("Sorry, we're experiencing technical difficulties. Please try again later."),
            media_type="application/xml"
        )


# =======================
# VOICE ENDPOINTS (ElevenLabs)
# =======================

@router.post(
    "/{tenant_id}/voice/knowledge",
    tags=["Voice"],
    summary="ElevenLabs knowledge base webhook",
    description="Retrieve knowledge base information during voice calls"
)
async def voice_knowledge_webhook(
    tenant_id: str,
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    ElevenLabs webhook endpoint for knowledge base retrieval during calls.

    Args:
        tenant_id: Tenant identifier
        request: JSON payload with query
        db: Database session

    Returns:
        JSON response with knowledge base answer
    """
    from core.backend.services.voice_service import VoiceService

    query = request.get("query", "")
    conversation_id = request.get("conversation_id", "")
    caller_phone = request.get("caller_phone", "")

    logger.info(f"Voice knowledge request from {caller_phone}: {query}")

    try:
        # Get tenant
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_id).first()
        if not tenant:
            logger.error(f"Tenant {tenant_id} not found")
            return {
                "response": "Service unavailable",
                "metadata": {"error": "tenant_not_found"}
            }

        # Generate AI response using knowledge base
        chat_service = ChatService(tenant_id, db)
        ai_response = await chat_service.generate_response(query, caller_phone)

        # Format response for ElevenLabs
        voice_service = VoiceService(
            api_key=tenant.config.get("elevenlabs", {}).get("api_key", ""),
            agent_id=tenant.config.get("elevenlabs", {}).get("agent_id", "")
        )

        formatted_response = voice_service.format_knowledge_base_response(
            query=query,
            answer=ai_response["message"],
            documents=ai_response.get("documents", []),
            confidence=ai_response.get("confidence", 0)
        )

        logger.info(f"Voice knowledge response generated for {caller_phone}")
        return formatted_response

    except Exception as e:
        logger.error(f"Error processing voice knowledge webhook: {str(e)}")
        return {
            "response": "I apologize, but I'm having trouble accessing that information right now. Please try again or speak with our team directly.",
            "metadata": {"error": str(e)}
        }


@router.post(
    "/{tenant_id}/voice/transcript",
    tags=["Voice"],
    summary="ElevenLabs conversation logging webhook",
    description="Log voice conversation transcripts"
)
async def voice_transcript_webhook(
    tenant_id: str,
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    ElevenLabs webhook endpoint for logging call transcripts.

    Args:
        tenant_id: Tenant identifier
        request: JSON payload with transcript data
        db: Database session

    Returns:
        Success confirmation
    """
    from core.backend.services.voice_service import VoiceService
    from core.database.models import Conversation, Message, MessageRole

    conversation_id = request.get("conversation_id", "")
    caller_phone = request.get("caller_phone", "")
    messages = request.get("messages", [])
    duration_seconds = request.get("duration_seconds")

    logger.info(f"Voice transcript received for {caller_phone}: {len(messages)} messages")

    try:
        # Get tenant
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_id).first()
        if not tenant:
            logger.error(f"Tenant {tenant_id} not found")
            return {"success": False, "error": "tenant_not_found"}

        # Get or create conversation
        conversation = db.query(Conversation).filter(
            Conversation.tenant_id == tenant.id,
            Conversation.session_id == caller_phone,
            Conversation.channel == "voice"
        ).first()

        if not conversation:
            conversation = Conversation(
                id=uuid4(),
                tenant_id=tenant.id,
                session_id=caller_phone,
                channel="voice"
            )
            db.add(conversation)
            db.commit()
            logger.info(f"Created new voice conversation for {caller_phone}")

        # Save all messages from transcript
        for msg in messages:
            role = MessageRole.USER if msg.get("role") == "user" else MessageRole.ASSISTANT

            message = Message(
                id=uuid4(),
                conversation_id=conversation.id,
                tenant_id=tenant.id,
                role=role,
                content=msg.get("content", ""),
                extra_data={
                    "channel": "voice",
                    "timestamp": msg.get("timestamp"),
                    "conversation_id": conversation_id,
                    "caller_phone": caller_phone
                }
            )
            db.add(message)

        # Update conversation metadata
        conversation.extra_data = {
            "elevenlabs_conversation_id": conversation_id,
            "duration_seconds": duration_seconds,
            "caller_phone": caller_phone
        }

        db.commit()

        logger.info(f"Voice transcript saved for {caller_phone}: {len(messages)} messages")

        return {
            "success": True,
            "conversation_id": str(conversation.id),
            "messages_saved": len(messages)
        }

    except Exception as e:
        logger.error(f"Error processing voice transcript webhook: {str(e)}")
        db.rollback()
        return {"success": False, "error": str(e)}
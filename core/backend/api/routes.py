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
from core.database.base import get_db
from core.database.models import Tenant, KnowledgeDoc
from core.shared.config_loader import TenantConfig

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

    # Verify API key against database
    tenant = db.query(Tenant).filter(
        Tenant.slug == tenant_id,
        Tenant.api_key == x_api_key
    ).first()

    if not tenant:
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
        # Load tenant configuration
        config = TenantConfig(tenant_id)

        return TenantConfigResponse(
            slug=tenant_id,
            name=config.get("tenant.name", tenant.name),
            branding=config.branding,
            features=config.features,
            business_info=config.business_info,
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
"""Database operations service for conversation and message management."""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from core.database.models import Conversation, Message, Tenant, ResolutionStatus, MessageRole

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Handles all database operations for conversations and messages.

    CRITICAL: All queries MUST filter by tenant_id for security.
    """

    def __init__(self, db: Session, tenant_id: str):
        """
        Initialize database service.

        Args:
            db: SQLAlchemy database session
            tenant_id: Tenant slug for isolation
        """
        self.db = db
        self.tenant_slug = tenant_id
        self._tenant_uuid: Optional[UUID] = None

    def _get_tenant_uuid(self) -> UUID:
        """
        Get tenant UUID from slug (cached).

        Returns:
            Tenant UUID

        Raises:
            ValueError: If tenant not found
        """
        if self._tenant_uuid is None:
            tenant = self.db.query(Tenant).filter(
                Tenant.slug == self.tenant_slug
            ).first()

            if not tenant:
                raise ValueError(f"Tenant not found: {self.tenant_slug}")

            self._tenant_uuid = tenant.id
            logger.info(f"Loaded tenant UUID for {self.tenant_slug}: {self._tenant_uuid}")

        return self._tenant_uuid

    async def get_or_create_conversation(
        self,
        session_id: str,
        channel: str = "chat"
    ) -> Conversation:
        """
        Get existing conversation or create new one.

        Args:
            session_id: Session identifier
            channel: Communication channel (chat, email, sms, etc.)

        Returns:
            Conversation object
        """
        tenant_uuid = self._get_tenant_uuid()

        # Try to find existing conversation
        conversation = self.db.query(Conversation).filter(
            Conversation.tenant_id == tenant_uuid,
            Conversation.session_id == session_id,
            Conversation.ended_at.is_(None)  # Only active conversations
        ).first()

        if conversation:
            logger.debug(f"Found existing conversation: {conversation.id}")
            return conversation

        # Create new conversation
        conversation = Conversation(
            id=uuid4(),
            tenant_id=tenant_uuid,
            session_id=session_id,
            channel=channel,
            started_at=datetime.utcnow(),
            resolution_status=ResolutionStatus.PENDING,
            escalated=False,
            extra_data={}
        )

        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)

        logger.info(f"Created new conversation: {conversation.id} for session: {session_id}")
        return conversation

    async def save_message(
        self,
        conversation_id: UUID,
        role: MessageRole,
        content: str,
        metadata: Optional[dict] = None
    ) -> Message:
        """
        Save a message to the database.

        Args:
            conversation_id: Conversation UUID
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional metadata (confidence, tokens, etc.)

        Returns:
            Created Message object
        """
        tenant_uuid = self._get_tenant_uuid()

        message = Message(
            id=uuid4(),
            conversation_id=conversation_id,
            tenant_id=tenant_uuid,
            role=role,
            content=content,
            extra_data=metadata or {},
            created_at=datetime.utcnow()
        )

        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)

        logger.debug(f"Saved {role.value} message: {message.id}")
        return message

    async def get_conversation_history(
        self,
        conversation_id: UUID,
        limit: int = 10
    ) -> List[Message]:
        """
        Get recent messages from a conversation.

        Args:
            conversation_id: Conversation UUID
            limit: Maximum number of messages to return

        Returns:
            List of Message objects, ordered chronologically
        """
        tenant_uuid = self._get_tenant_uuid()

        messages = self.db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.tenant_id == tenant_uuid  # CRITICAL: Tenant isolation
        ).order_by(
            Message.created_at.asc()
        ).limit(limit).all()

        logger.debug(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
        return messages

    async def update_conversation_status(
        self,
        conversation_id: UUID,
        status: Optional[ResolutionStatus] = None,
        escalated: Optional[bool] = None
    ) -> Conversation:
        """
        Update conversation status and escalation flag.

        Args:
            conversation_id: Conversation UUID
            status: New resolution status (optional)
            escalated: New escalation flag (optional)

        Returns:
            Updated Conversation object

        Raises:
            ValueError: If conversation not found
        """
        tenant_uuid = self._get_tenant_uuid()

        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_uuid  # CRITICAL: Tenant isolation
        ).first()

        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")

        # Update fields
        if status is not None:
            conversation.resolution_status = status
            logger.info(f"Updated conversation {conversation_id} status to {status.value}")

        if escalated is not None:
            conversation.escalated = escalated
            logger.info(f"Updated conversation {conversation_id} escalated to {escalated}")

        # Mark as ended if resolved or escalated
        if status in [ResolutionStatus.RESOLVED, ResolutionStatus.ESCALATED]:
            if conversation.ended_at is None:
                conversation.ended_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(conversation)

        return conversation

    async def get_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        """
        Get a conversation by ID.

        Args:
            conversation_id: Conversation UUID

        Returns:
            Conversation object or None if not found
        """
        tenant_uuid = self._get_tenant_uuid()

        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_uuid  # CRITICAL: Tenant isolation
        ).first()

        return conversation
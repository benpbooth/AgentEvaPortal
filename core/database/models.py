"""SQLAlchemy database models."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    JSON,
    Integer,
    Float,
    Boolean,
    Text,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, CHAR
import enum
import uuid as uuid_lib

from core.database.base import Base


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid_lib.UUID):
                return str(value)
            else:
                return str(uuid_lib.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if isinstance(value, uuid_lib.UUID):
                return value
            else:
                return uuid_lib.UUID(value)


class TenantStatus(str, enum.Enum):
    """Tenant status enumeration."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    CANCELLED = "cancelled"


class ResolutionStatus(str, enum.Enum):
    """Conversation resolution status."""

    RESOLVED = "resolved"
    ESCALATED = "escalated"
    PENDING = "pending"
    ABANDONED = "abandoned"


class MessageRole(str, enum.Enum):
    """Message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Tenant(Base):
    """Tenant model - represents a client/organization."""

    __tablename__ = "tenants"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=True)
    config = Column(JSON, nullable=False, default=dict)
    status = Column(
        SQLEnum(TenantStatus),
        nullable=False,
        default=TenantStatus.TRIAL,
        index=True,
    )
    api_key = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    conversations = relationship("Conversation", back_populates="tenant", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="tenant", cascade="all, delete-orphan")
    knowledge_docs = relationship("KnowledgeDoc", back_populates="tenant", cascade="all, delete-orphan")
    analytics = relationship("Analytics", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Tenant(slug='{self.slug}', name='{self.name}', status='{self.status}')>"


class Conversation(Base):
    """Conversation model - represents a chat session."""

    __tablename__ = "conversations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(GUID, ForeignKey("tenants.id"), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    channel = Column(String(50), nullable=False, default="web")  # web, mobile, email, etc.
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    resolution_status = Column(
        SQLEnum(ResolutionStatus),
        nullable=False,
        default=ResolutionStatus.PENDING,
        index=True,
    )
    escalated = Column(Boolean, default=False, nullable=False, index=True)
    extra_data = Column("metadata", JSON, nullable=False, default=dict)

    # Relationships
    tenant = relationship("Tenant", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Conversation(id='{self.id}', session_id='{self.session_id}', status='{self.resolution_status}')>"


class Message(Base):
    """Message model - represents a single message in a conversation."""

    __tablename__ = "messages"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    conversation_id = Column(GUID, ForeignKey("conversations.id"), nullable=False, index=True)
    tenant_id = Column(GUID, ForeignKey("tenants.id"), nullable=False, index=True)
    role = Column(SQLEnum(MessageRole), nullable=False, index=True)
    content = Column(Text, nullable=False)
    extra_data = Column("metadata", JSON, nullable=False, default=dict)  # Store confidence, tokens, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="messages")
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id='{self.id}', role='{self.role}', content='{self.content[:50]}...')>"


class KnowledgeDoc(Base):
    """Knowledge document model - represents a document in the knowledge base."""

    __tablename__ = "knowledge_docs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(GUID, ForeignKey("tenants.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    extra_data = Column("metadata", JSON, nullable=False, default=dict)  # Source, category, tags, etc.
    vector_id = Column(String(255), nullable=True, index=True)  # Pinecone vector ID
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="knowledge_docs")

    def __repr__(self) -> str:
        return f"<KnowledgeDoc(id='{self.id}', title='{self.title}')>"


class Analytics(Base):
    """Analytics model - stores daily aggregated metrics per tenant."""

    __tablename__ = "analytics"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(GUID, ForeignKey("tenants.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    total_conversations = Column(Integer, nullable=False, default=0)
    resolved_conversations = Column(Integer, nullable=False, default=0)
    escalated_conversations = Column(Integer, nullable=False, default=0)
    avg_response_time_ms = Column(Float, nullable=True)
    avg_csat_score = Column(Float, nullable=True)
    extra_data = Column("metadata", JSON, nullable=False, default=dict)  # Additional metrics

    # Relationships
    tenant = relationship("Tenant", back_populates="analytics")

    def __repr__(self) -> str:
        return f"<Analytics(tenant_id='{self.tenant_id}', date='{self.date}', total={self.total_conversations})>"
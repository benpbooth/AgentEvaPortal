"""Chat service for processing messages with OpenAI integration."""

import logging
import re
from typing import Dict, Any, List, Optional
from uuid import uuid4

from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from core.backend.config import get_settings
from core.backend.services.database_service import DatabaseService
from core.backend.services.retrieval_service import RetrievalService
from core.database.models import MessageRole, ResolutionStatus, Tenant

logger = logging.getLogger(__name__)
settings = get_settings()


class TenantConfigHelper:
    """Helper class to access tenant config from database with dot notation."""

    def __init__(self, config_dict: dict):
        self._config = config_dict or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value using dot notation (e.g., 'ai.model')."""
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value


class ChatService:
    """
    Main service for processing chat messages with AI.

    Handles:
    - Loading tenant configuration
    - Retrieving conversation history
    - Searching knowledge base
    - Calling OpenAI API
    - Checking escalation conditions
    - Saving messages to database
    """

    def __init__(self, tenant_id: str, db: Session):
        """
        Initialize chat service for a tenant.

        Args:
            tenant_id: Tenant slug
            db: SQLAlchemy database session
        """
        self.tenant_id = tenant_id
        self.db = db

        # Load tenant from database
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Load tenant configuration from database
        self.config = TenantConfigHelper(tenant.config or {})
        logger.info(f"Loaded configuration for tenant: {tenant_id}")

        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Initialize services
        self.db_service = DatabaseService(db, tenant_id)
        self.retrieval_service = RetrievalService(tenant_id)

        logger.info(f"Initialized ChatService for tenant: {tenant_id}")

    async def process_message(
        self,
        message: str,
        session_id: str,
        channel: str = "chat"
    ) -> Dict[str, Any]:
        """
        Process a user message and return AI response.

        Args:
            message: User's message text
            session_id: Session identifier for conversation continuity
            channel: Communication channel (chat, email, sms, etc.)

        Returns:
            Dictionary with:
                - response: AI assistant's response text
                - escalate: Whether to escalate to human agent
                - confidence: Confidence score (0-1)
                - session_id: Session identifier
                - conversation_id: Conversation UUID
        """
        try:
            logger.info(f"Processing message for tenant {self.tenant_id}, session: {session_id}")

            # Step 1: Get or create conversation
            conversation = await self.db_service.get_or_create_conversation(
                session_id=session_id,
                channel=channel
            )

            # Step 2: Save user message
            await self.db_service.save_message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=message,
                metadata={"channel": channel}
            )

            # Step 3: Get conversation history
            history = await self.db_service.get_conversation_history(
                conversation_id=conversation.id,
                limit=10
            )

            # Step 4: Search knowledge base
            relevant_docs = await self.retrieval_service.search(
                query=message,
                top_k=5
            )

            # Step 5: Build context from documents
            context = self._build_context(relevant_docs)

            # Step 6: Generate AI response
            ai_response, confidence = await self._generate_response(
                user_message=message,
                conversation_history=history,
                context=context
            )

            # Step 7: Check for escalation
            should_escalate = self._check_escalation(
                user_message=message,
                ai_response=ai_response,
                conversation=conversation
            )

            # Step 8: Save AI response
            await self.db_service.save_message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=ai_response,
                metadata={
                    "confidence": confidence,
                    "escalation_triggered": should_escalate,
                    "documents_used": len(relevant_docs)
                }
            )

            # Step 9: Update conversation status if escalating
            if should_escalate:
                await self.db_service.update_conversation_status(
                    conversation_id=conversation.id,
                    status=ResolutionStatus.ESCALATED,
                    escalated=True
                )
                logger.warning(f"Conversation {conversation.id} escalated to human agent")

            # Step 10: Return response
            return {
                "response": ai_response,
                "escalate": should_escalate,
                "confidence": confidence,
                "session_id": session_id,
                "conversation_id": str(conversation.id)
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return self._error_response(session_id, str(e))

    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """
        Build context string from retrieved documents.

        Args:
            documents: List of relevant documents from knowledge base

        Returns:
            Formatted context string
        """
        if not documents:
            return ""

        context_parts = ["Here is relevant information from our knowledge base:\n"]

        for i, doc in enumerate(documents, 1):
            title = doc.get("title", "Document")
            content = doc.get("content", "")
            context_parts.append(f"\n[Source {i}: {title}]\n{content}\n")

        return "\n".join(context_parts)

    async def _generate_response(
        self,
        user_message: str,
        conversation_history: List,
        context: str
    ) -> tuple[str, float]:
        """
        Generate AI response using OpenAI.

        Args:
            user_message: Current user message
            conversation_history: Previous messages
            context: Context from knowledge base

        Returns:
            Tuple of (response_text, confidence_score)
        """
        try:
            # Get AI configuration from tenant settings
            ai_config = self.config.get("ai_config", {})
            model = ai_config.get("model", "gpt-4o-mini")
            temperature = ai_config.get("temperature", 0.7)
            max_tokens = ai_config.get("max_tokens", 500)

            # Build system prompt
            system_prompt = self._build_system_prompt(context)

            # Build messages array
            messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history (last 10 messages)
            for msg in conversation_history[-10:]:
                messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

            # Add current user message if not already in history
            if not conversation_history or conversation_history[-1].content != user_message:
                messages.append({
                    "role": "user",
                    "content": user_message
                })

            logger.debug(f"Calling OpenAI with model: {model}, temperature: {temperature}")

            # Call OpenAI API
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Extract response
            ai_message = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            # Calculate confidence (simplified)
            confidence = 0.9 if finish_reason == "stop" else 0.7

            logger.info(f"Generated response with confidence: {confidence}")
            return ai_message, confidence

        except Exception as e:
            logger.error(f"OpenAI API error: {e}", exc_info=True)
            # Return fallback response
            ai_config = self.config.get("ai_config", {})
            fallback_responses = ai_config.get(
                "fallback_responses",
                ["I'm having trouble processing that right now. Please try again or contact support."]
            )
            if isinstance(fallback_responses, list) and fallback_responses:
                return fallback_responses[0], 0.5
            return "I'm having trouble processing that right now. Please try again or contact support.", 0.5

    def _build_system_prompt(self, context: str) -> str:
        """
        Build system prompt for OpenAI.

        Args:
            context: Knowledge base context

        Returns:
            Complete system prompt
        """
        # Get base prompt from config
        ai_config = self.config.get("ai_config", {})
        base_prompt = ai_config.get("system_prompt", "You are a helpful customer support assistant.")

        # Get business info
        branding = self.config.get("branding", {})
        business_name = branding.get("company_name", self.tenant_id)
        business_email = branding.get("support_email", "")

        # Build prompt (simple version without format placeholders to avoid KeyErrors)
        prompt = f"{base_prompt}\n\nCompany: {business_name}"
        if business_email:
            prompt += f"\nSupport Email: {business_email}"

        # Append context if available
        if context:
            prompt += f"\n\n{context}"

        return prompt

    def _check_escalation(
        self,
        user_message: str,
        ai_response: str,
        conversation: Any
    ) -> bool:
        """
        Check if conversation should be escalated to human agent.

        Args:
            user_message: User's message
            ai_response: AI's response
            conversation: Conversation object

        Returns:
            True if should escalate, False otherwise
        """
        # Check 1: Escalation keywords
        ai_config = self.config.get("ai_config", {})
        keywords = ai_config.get("escalation_keywords", [])
        combined_text = f"{user_message} {ai_response}".lower()

        for keyword in keywords:
            if keyword.lower() in combined_text:
                logger.info(f"Escalation triggered by keyword: {keyword}")
                return True

        # Check 2: Conversation length threshold (disabled by default)
        message_threshold = 999  # Very high threshold by default
        message_count = len(conversation.messages) if hasattr(conversation, 'messages') else 0

        if message_count >= message_threshold:
            logger.info(f"Escalation triggered by message count: {message_count}")
            return True

        return False

    def _error_response(self, session_id: str, error_details: str) -> Dict[str, Any]:
        """
        Generate error response.

        Args:
            session_id: Session identifier
            error_details: Error message

        Returns:
            Error response dictionary
        """
        logger.error(f"Returning error response: {error_details}")

        error_message = (
            "I apologize, but I'm experiencing technical difficulties right now. "
            "Please try again in a moment, or contact our support team for immediate assistance."
        )

        return {
            "response": error_message,
            "escalate": True,  # Escalate on errors
            "confidence": 0.0,
            "session_id": session_id,
            "conversation_id": str(uuid4())  # Generate temporary ID
        }
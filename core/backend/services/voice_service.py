"""
Voice Service - Handles ElevenLabs Conversational AI integration
"""
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class VoiceService:
    """Service for ElevenLabs voice agent integration."""

    def __init__(self, api_key: str, agent_id: str):
        """
        Initialize voice service with ElevenLabs credentials.

        Args:
            api_key: ElevenLabs API key
            agent_id: ElevenLabs agent ID
        """
        self.api_key = api_key
        self.agent_id = agent_id
        self.base_url = "https://api.elevenlabs.io/v1"

    def format_knowledge_base_response(
        self,
        query: str,
        answer: str,
        documents: list,
        confidence: float
    ) -> Dict[str, Any]:
        """
        Format knowledge base response for ElevenLabs.

        Args:
            query: User's question
            answer: AI-generated answer
            documents: List of relevant documents used
            confidence: Confidence score

        Returns:
            Formatted response dictionary
        """
        return {
            "response": answer,
            "metadata": {
                "query": query,
                "confidence": confidence,
                "documents_used": len(documents),
                "source": "agenteva_knowledge_base"
            }
        }

    @staticmethod
    def format_conversation_transcript(
        conversation_id: str,
        messages: list,
        caller_phone: str,
        duration_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Format conversation transcript for logging.

        Args:
            conversation_id: Unique conversation identifier
            messages: List of messages in conversation
            caller_phone: Caller's phone number
            duration_seconds: Call duration in seconds

        Returns:
            Formatted transcript dictionary
        """
        return {
            "conversation_id": conversation_id,
            "caller_phone": caller_phone,
            "duration_seconds": duration_seconds,
            "message_count": len(messages),
            "messages": [
                {
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "timestamp": msg.get("timestamp")
                }
                for msg in messages
            ]
        }

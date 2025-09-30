"""Retrieval service for knowledge base search using vector embeddings."""

import logging
from typing import List, Dict, Any, Optional
import re

from openai import AsyncOpenAI
from pinecone import Pinecone, ServerlessSpec

from core.backend.config import get_settings

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    Handles knowledge base retrieval using vector search with Pinecone.

    Uses OpenAI's text-embedding-3-small model for embeddings.
    """

    # Class-level Pinecone client (shared across instances)
    _pinecone_client: Optional[Pinecone] = None
    _index_name = "agenteva-knowledge"

    def __init__(self, tenant_id: str):
        """
        Initialize retrieval service for a tenant.

        Args:
            tenant_id: Tenant identifier (slug)
        """
        self.tenant_id = tenant_id
        settings = get_settings()
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Initialize Pinecone client (singleton pattern)
        if RetrievalService._pinecone_client is None:
            try:
                RetrievalService._pinecone_client = Pinecone(api_key=settings.pinecone_api_key)
                logger.info("Pinecone client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Pinecone: {e}")
                RetrievalService._pinecone_client = None

        self.pc = RetrievalService._pinecone_client

        # Ensure index exists after pc is set
        if self.pc:
            self._ensure_index_exists()

        logger.debug(f"Initialized RetrievalService for tenant: {tenant_id}")

    def _ensure_index_exists(self):
        """Create Pinecone index if it doesn't exist."""
        if not self.pc:
            return

        try:
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]

            if self._index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index: {self._index_name}")
                self.pc.create_index(
                    name=self._index_name,
                    dimension=1536,  # text-embedding-3-small dimension
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
                logger.info(f"Pinecone index created: {self._index_name}")
        except Exception as e:
            logger.error(f"Error ensuring index exists: {e}")

    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using OpenAI.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        try:
            response = await self.openai_client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search knowledge base for relevant documents using vector similarity.

        Args:
            query: Search query text
            top_k: Number of top results to return
            score_threshold: Minimum similarity score (0-1)

        Returns:
            List of document dictionaries with keys:
                - id: Document ID
                - content: Document text
                - title: Document title
                - score: Similarity score
                - metadata: Additional document metadata
        """
        logger.debug(f"Search query for tenant {self.tenant_id}: {query[:50]}...")

        if not self.pc:
            logger.warning("Pinecone not initialized, returning empty results")
            return []

        try:
            # 1. Generate embedding for query
            query_embedding = await self._generate_embedding(query)

            # 2. Query Pinecone with tenant isolation
            index = self.pc.Index(self._index_name)
            results = index.query(
                vector=query_embedding,
                top_k=top_k,
                filter={"tenant_id": self.tenant_id},  # CRITICAL: Tenant isolation
                include_metadata=True
            )

            # 3. Filter by score threshold and format results
            documents = []
            for match in results.matches:
                if match.score >= score_threshold:
                    documents.append({
                        "id": match.id,
                        "content": match.metadata.get("content", ""),
                        "title": match.metadata.get("title", ""),
                        "score": match.score,
                        "metadata": match.metadata
                    })

            logger.info(f"Found {len(documents)} relevant documents for query")
            return documents

        except Exception as e:
            logger.error(f"Error during vector search: {e}", exc_info=True)
            return []

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks for embedding.

        Args:
            text: Text to chunk
            chunk_size: Maximum characters per chunk
            overlap: Character overlap between chunks

        Returns:
            List of text chunks
        """
        # Clean and normalize text
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for period, question mark, or exclamation
                for boundary in ['. ', '? ', '! ', '\n']:
                    last_boundary = text.rfind(boundary, start, end)
                    if last_boundary > start:
                        end = last_boundary + 1
                        break

            chunks.append(text[start:end].strip())
            start = end - overlap if end < len(text) else end

        return chunks

    async def index_document(
        self,
        document_id: str,
        title: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Index a document into the knowledge base with chunking.

        Args:
            document_id: Unique document identifier
            title: Document title
            content: Document text content
            metadata: Additional metadata (source, category, tags, etc.)

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Indexing document for tenant {self.tenant_id}: {document_id}")

        if not self.pc:
            logger.error("Pinecone not initialized, cannot index document")
            return False

        try:
            # 1. Chunk the content
            chunks = self._chunk_text(content)
            logger.debug(f"Split document into {len(chunks)} chunks")

            # 2. Generate embeddings for each chunk
            vectors = []
            for i, chunk in enumerate(chunks):
                embedding = await self._generate_embedding(chunk)

                # Create unique ID for this chunk
                vector_id = f"{document_id}_{i}" if len(chunks) > 1 else document_id

                # Prepare metadata with tenant isolation
                chunk_metadata = {
                    "tenant_id": self.tenant_id,  # CRITICAL: Tenant isolation
                    "document_id": document_id,
                    "title": title,
                    "content": chunk,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    **metadata  # Include any additional metadata
                }

                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": chunk_metadata
                })

            # 3. Upsert to Pinecone
            index = self.pc.Index(self._index_name)
            index.upsert(vectors=vectors)

            logger.info(f"Successfully indexed {len(vectors)} vectors for document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Error indexing document {document_id}: {e}", exc_info=True)
            return False

    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document and all its chunks from the knowledge base.

        Args:
            document_id: Document identifier to delete

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Deleting document for tenant {self.tenant_id}: {document_id}")

        if not self.pc:
            logger.error("Pinecone not initialized, cannot delete document")
            return False

        try:
            index = self.pc.Index(self._index_name)

            # Delete by filter (document_id and tenant_id for security)
            index.delete(
                filter={
                    "document_id": document_id,
                    "tenant_id": self.tenant_id  # CRITICAL: Tenant isolation
                }
            )

            logger.info(f"Successfully deleted document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}", exc_info=True)
            return False
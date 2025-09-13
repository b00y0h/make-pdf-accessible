"""
Bedrock Titan Embeddings Service for LLM corpus preparation
"""

import json
import logging
from datetime import datetime
from typing import Any

import boto3
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Service for generating and managing document embeddings using Bedrock Titan."""

    def __init__(self):
        self.bedrock = boto3.client("bedrock-runtime")
        self.s3 = boto3.client("s3")
        self.model_id = "amazon.titan-embed-text-v1"
        self.dimensions = 1536  # Titan text embeddings dimension

    def generate_embeddings_for_corpus(
        self,
        doc_id: str,
        document_corpus: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Generate embeddings for all chunks in a document corpus.

        Args:
            doc_id: Document identifier
            document_corpus: Document corpus with chunks

        Returns:
            Enhanced corpus with embeddings
        """
        try:
            logger.info(f"Generating embeddings for document {doc_id}")

            chunks = document_corpus.get("chunks", [])
            embeddings = []

            # Process chunks in batches to avoid rate limiting
            batch_size = 10
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                batch_embeddings = self._generate_batch_embeddings(batch)
                embeddings.extend(batch_embeddings)

                logger.info(f"Generated embeddings for batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}")

            # Update corpus with embeddings
            enhanced_corpus = document_corpus.copy()
            enhanced_corpus["embeddings"] = embeddings
            enhanced_corpus["embeddingModel"] = self.model_id
            enhanced_corpus["embeddingDimensions"] = self.dimensions
            enhanced_corpus["embeddingsGeneratedAt"] = datetime.utcnow()

            logger.info(f"Generated {len(embeddings)} embeddings for document {doc_id}")
            return enhanced_corpus

        except Exception as e:
            logger.error(f"Failed to generate embeddings for document {doc_id}: {e}")
            raise

    def _generate_batch_embeddings(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Generate embeddings for a batch of chunks."""

        embeddings = []

        for chunk in chunks:
            try:
                # Use cleanedContent for embedding generation
                content = chunk.get("cleanedContent", chunk.get("content", ""))

                if not content.strip():
                    logger.warning(f"Skipping empty chunk {chunk.get('id')}")
                    continue

                # Truncate content if too long (Titan has token limits)
                if len(content) > 7000:  # Conservative limit
                    content = content[:7000] + "..."
                    logger.info(f"Truncated content for chunk {chunk.get('id')}")

                # Generate embedding
                embedding_vector = self._generate_single_embedding(content)

                if embedding_vector:
                    embedding = {
                        "id": f"{chunk.get('docId')}_emb_{chunk.get('chunkIndex')}",
                        "chunkId": chunk.get("id"),
                        "docId": chunk.get("docId"),
                        "vector": embedding_vector,
                        "model": self.model_id,
                        "dimensions": len(embedding_vector),
                        "contentPreview": content[:100],
                        "createdAt": datetime.utcnow(),
                        "modelVersion": "v1",
                    }
                    embeddings.append(embedding)

            except Exception as e:
                logger.error(f"Failed to generate embedding for chunk {chunk.get('id')}: {e}")
                # Continue with other chunks
                continue

        return embeddings

    def _generate_single_embedding(self, text: str) -> list[float] | None:
        """Generate a single embedding vector using Bedrock Titan."""

        try:
            # Prepare request payload
            payload = {
                "inputText": text
            }

            # Call Bedrock Titan embeddings
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload)
            )

            # Parse response
            result = json.loads(response["body"].read())
            embedding = result.get("embedding", [])

            if not embedding:
                logger.error("No embedding returned from Bedrock")
                return None

            # Validate embedding dimensions
            if len(embedding) != self.dimensions:
                logger.warning(f"Unexpected embedding dimensions: {len(embedding)} (expected {self.dimensions})")

            return embedding

        except Exception as e:
            logger.error(f"Bedrock embeddings API call failed: {e}")
            return None

    def calculate_similarity(self, vector1: list[float], vector2: list[float]) -> float:
        """Calculate cosine similarity between two embedding vectors."""

        try:
            # Convert to numpy arrays
            vec1 = np.array(vector1)
            vec2 = np.array(vector2)

            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return float(similarity)

        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0

    def find_similar_chunks(
        self,
        query_embedding: list[float],
        document_embeddings: list[dict[str, Any]],
        top_k: int = 10,
        min_similarity: float = 0.5
    ) -> list[dict[str, Any]]:
        """
        Find the most similar chunks to a query embedding.

        Args:
            query_embedding: Query vector
            document_embeddings: List of chunk embeddings
            top_k: Number of top results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of similar chunks with similarity scores
        """
        try:
            similarities = []

            for embedding_data in document_embeddings:
                chunk_vector = embedding_data.get("vector", [])
                if not chunk_vector:
                    continue

                similarity = self.calculate_similarity(query_embedding, chunk_vector)

                if similarity >= min_similarity:
                    similarities.append({
                        "chunkId": embedding_data.get("chunkId"),
                        "docId": embedding_data.get("docId"),
                        "similarity": similarity,
                        "contentPreview": embedding_data.get("contentPreview"),
                        "embedding": embedding_data,
                    })

            # Sort by similarity (descending) and return top-k
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            return similarities[:top_k]

        except Exception as e:
            logger.error(f"Error finding similar chunks: {e}")
            return []

    def save_embeddings_to_s3(
        self,
        doc_id: str,
        embeddings: list[dict[str, Any]],
        bucket_name: str
    ) -> str:
        """
        Save embeddings to S3 for later retrieval.

        Args:
            doc_id: Document identifier
            embeddings: List of embeddings
            bucket_name: S3 bucket name

        Returns:
            S3 key where embeddings were saved
        """
        try:
            s3_key = f"embeddings/{doc_id}/titan_embeddings.json"

            # Prepare embeddings data for storage
            embeddings_data = {
                "docId": doc_id,
                "model": self.model_id,
                "dimensions": self.dimensions,
                "totalEmbeddings": len(embeddings),
                "embeddings": embeddings,
                "createdAt": datetime.utcnow().isoformat(),
            }

            # Upload to S3
            self.s3.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=json.dumps(embeddings_data, default=str),
                ContentType="application/json",
            )

            logger.info(f"Saved {len(embeddings)} embeddings to {s3_key}")
            return s3_key

        except Exception as e:
            logger.error(f"Failed to save embeddings to S3: {e}")
            raise

    def load_embeddings_from_s3(
        self,
        s3_key: str,
        bucket_name: str
    ) -> list[dict[str, Any]] | None:
        """
        Load embeddings from S3.

        Args:
            s3_key: S3 key for embeddings file
            bucket_name: S3 bucket name

        Returns:
            List of embeddings or None if not found
        """
        try:
            response = self.s3.get_object(Bucket=bucket_name, Key=s3_key)
            embeddings_data = json.loads(response["Body"].read())

            embeddings = embeddings_data.get("embeddings", [])
            logger.info(f"Loaded {len(embeddings)} embeddings from {s3_key}")

            return embeddings

        except Exception as e:
            logger.error(f"Failed to load embeddings from S3: {e}")
            return None

    def generate_query_embedding(self, query_text: str) -> list[float] | None:
        """Generate embedding for a search query."""

        # Clean query text
        cleaned_query = query_text.strip()
        if not cleaned_query:
            return None

        return self._generate_single_embedding(cleaned_query)

    def prepare_embedding_batch(
        self,
        chunks: list[dict[str, Any]],
        include_context: bool = True
    ) -> list[str]:
        """
        Prepare text content for embedding generation.

        Args:
            chunks: List of text chunks
            include_context: Whether to include section context

        Returns:
            List of prepared text strings for embedding
        """
        prepared_texts = []

        for chunk in chunks:
            # Start with cleaned content
            text = chunk.get("cleanedContent", chunk.get("content", ""))

            # Add context if requested
            if include_context:
                section_path = chunk.get("sectionPath", [])
                if section_path:
                    context = " > ".join(section_path)
                    text = f"Section: {context}\n\n{text}"

                # Add type context
                chunk_type = chunk.get("type", "text")
                if chunk_type != "text":
                    text = f"[{chunk_type.upper()}] {text}"

                # Add alt-text for figures
                if chunk_type == "figure" and chunk.get("altText"):
                    alt_text = chunk.get("altText")
                    text = f"{text}\nAlt text: {alt_text}"

            prepared_texts.append(text)

        return prepared_texts


# Global service instance
_embeddings_service = None


def get_embeddings_service() -> EmbeddingsService:
    """Get global embeddings service instance."""
    global _embeddings_service
    if _embeddings_service is None:
        _embeddings_service = EmbeddingsService()
    return _embeddings_service

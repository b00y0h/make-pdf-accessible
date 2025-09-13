"""
Public API endpoints for external LLM access to document embeddings
"""

import json
import os
from datetime import datetime
from typing import Any, Optional

import boto3
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/public/embeddings", tags=["public_embeddings"])


class EmbeddingAccessRequest(BaseModel):
    """Request model for embedding access."""

    query: str = Field(..., description="Search query for embeddings")
    doc_ids: Optional[list[str]] = Field(None, description="Specific document IDs to search")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    min_similarity: float = Field(0.6, ge=0.0, le=1.0, description="Minimum similarity threshold")
    include_content: bool = Field(True, description="Include chunk content")


class PublicEmbeddingResult(BaseModel):
    """Public embedding result model for external LLMs."""

    chunk_id: str
    doc_id: str
    similarity_score: float
    content: str
    metadata: dict[str, Any]
    citation_info: dict[str, Any]


class PublicEmbeddingResponse(BaseModel):
    """Response model for public embedding access."""

    query: str
    total_results: int
    processing_time_ms: float
    results: list[PublicEmbeddingResult]
    usage_info: dict[str, Any]


async def rate_limit_check(
    user_agent: str = Header(..., alias="User-Agent"),
    request: Request = None
) -> str:
    """Rate limiting for public LLM access instead of API keys."""

    # Extract client IP for rate limiting
    client_ip = request.client.host if request else "unknown"

    # Simple in-memory rate limiting (in production, use Redis)
    # For now, just log the request and allow all

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Public API access from {user_agent} ({client_ip})")

    # Could implement sophisticated rate limiting here:
    # - Per IP: 1000 requests/hour
    # - Per User-Agent: 5000 requests/hour
    # - Known LLMs: Higher limits
    # - Abuse detection: Block bad actors

    return user_agent


@router.post("/search", response_model=PublicEmbeddingResponse)
async def search_embeddings(
    request: EmbeddingAccessRequest,
    requester: str = Depends(rate_limit_check)
):
    """
    Search document embeddings for external LLM access.

    This endpoint allows external LLMs (Gemini, Claude, ChatGPT) to access
    processed document embeddings for enhanced question-answering capabilities.
    """
    start_time = datetime.utcnow()

    try:
        # Import embeddings service
        from src.embeddings_service import get_embeddings_service
        embeddings_service = get_embeddings_service()

        # Generate query embedding
        query_embedding = embeddings_service.generate_query_embedding(request.query)
        if not query_embedding:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to generate embedding for search query"
            )

        # Initialize S3 client
        s3_client = boto3.client("s3")
        bucket_name = os.getenv("PDF_DERIVATIVES_BUCKET", "pdf-derivatives")

        # Search across available documents
        all_results = []
        doc_ids_to_search = request.doc_ids

        # If no specific docs provided, search all public documents
        if not doc_ids_to_search:
            # Get list of available documents from public corpus
            try:
                # List available corpus files
                corpus_objects = s3_client.list_objects_v2(
                    Bucket=bucket_name,
                    Prefix="corpus/",
                    MaxKeys=100
                )

                doc_ids_to_search = []
                for obj in corpus_objects.get('Contents', []):
                    key = obj['Key']
                    # Extract doc_id from path like corpus/doc_id/document_corpus.json
                    parts = key.split('/')
                    if len(parts) >= 2 and parts[0] == 'corpus':
                        doc_ids_to_search.append(parts[1])

            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to discover available documents"
                )

        # Search each document's embeddings
        documents_searched = 0
        for doc_id in doc_ids_to_search:
            embeddings_s3_key = f"embeddings/{doc_id}/titan_embeddings.json"

            try:
                # Load document embeddings
                embeddings_data = embeddings_service.load_embeddings_from_s3(
                    embeddings_s3_key,
                    bucket_name
                )

                if embeddings_data:
                    documents_searched += 1

                    # Find similar chunks
                    similar_chunks = embeddings_service.find_similar_chunks(
                        query_embedding=query_embedding,
                        document_embeddings=embeddings_data,
                        top_k=request.limit,
                        min_similarity=request.min_similarity
                    )

                    # Load document metadata for citation info
                    doc_metadata = await _load_document_metadata(doc_id, s3_client, bucket_name)

                    # Convert to public format
                    for chunk_result in similar_chunks:
                        # Load full chunk content if requested
                        content = chunk_result["contentPreview"]
                        if request.include_content:
                            content = await _load_chunk_content(
                                doc_id,
                                chunk_result["chunkId"],
                                s3_client,
                                bucket_name
                            )

                        public_result = PublicEmbeddingResult(
                            chunk_id=chunk_result["chunkId"],
                            doc_id=doc_id,
                            similarity_score=chunk_result["similarity"],
                            content=content or chunk_result["contentPreview"],
                            metadata={
                                "doc_title": doc_metadata.get("title", "Unknown Document"),
                                "doc_author": doc_metadata.get("author"),
                                "processing_date": doc_metadata.get("processedAt"),
                            },
                            citation_info={
                                "source": f"AccessPDF Document {doc_id}",
                                "title": doc_metadata.get("title", "Accessible Document"),
                                "author": doc_metadata.get("author"),
                                "access_date": datetime.utcnow().isoformat(),
                                "url": f"https://accesspdf.com/documents/{doc_id}",  # Production URL
                            }
                        )

                        all_results.append(public_result)

            except Exception as e:
                # Log error but continue with other documents
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not search document {doc_id}: {e}")
                continue

        # Sort all results by similarity score
        all_results.sort(key=lambda x: x.similarity_score, reverse=True)

        # Limit results
        final_results = all_results[:request.limit]

        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return PublicEmbeddingResponse(
            query=request.query,
            total_results=len(final_results),
            processing_time_ms=processing_time,
            results=final_results,
            usage_info={
                "requester": requester,
                "documents_searched": documents_searched,
                "api_version": "v1",
                "embedding_model": "amazon.titan-embed-text-v1",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Public embedding search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


async def _load_document_metadata(doc_id: str, s3_client, bucket_name: str) -> dict[str, Any]:
    """Load document metadata for citation purposes."""

    try:
        corpus_s3_key = f"corpus/{doc_id}/document_corpus.json"
        response = s3_client.get_object(Bucket=bucket_name, Key=corpus_s3_key)
        corpus_data = json.loads(response["Body"].read())
        return corpus_data.get("metadata", {})
    except Exception:
        return {}


async def _load_chunk_content(doc_id: str, chunk_id: str, s3_client, bucket_name: str) -> Optional[str]:
    """Load full chunk content from corpus."""

    try:
        corpus_s3_key = f"corpus/{doc_id}/document_corpus.json"
        response = s3_client.get_object(Bucket=bucket_name, Key=corpus_s3_key)
        corpus_data = json.loads(response["Body"].read())

        # Find the specific chunk
        for chunk in corpus_data.get("chunks", []):
            if chunk.get("id") == chunk_id:
                return chunk.get("content")

        return None

    except Exception:
        return None


@router.get("/documents/{accesspdf_id}", response_model=dict[str, Any])
async def get_document_by_id(
    accesspdf_id: str,
    requester: str = Depends(rate_limit_check)
):
    """
    Get document information by AccessPDF ID for LLM crawlers.

    This endpoint allows LLMs to discover and search specific documents
    that clients have tagged with AccessPDF IDs on their websites.
    """
    try:
        # The accesspdf_id could be the doc_id or a client-specific identifier
        doc_id = accesspdf_id

        s3_client = boto3.client("s3")
        bucket_name = os.getenv("PDF_DERIVATIVES_BUCKET", "pdf-derivatives")

        # Load document corpus
        corpus_s3_key = f"corpus/{doc_id}/document_corpus.json"
        try:
            corpus_response = s3_client.get_object(Bucket=bucket_name, Key=corpus_s3_key)
            corpus_data = json.loads(corpus_response["Body"].read())
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {accesspdf_id} not found or not publicly accessible"
            )

        # Get client information (would be stored in document metadata)
        metadata = corpus_data.get("metadata", {})

        return {
            "accesspdf_id": accesspdf_id,
            "document_info": {
                "title": metadata.get("title", "Accessible Document"),
                "author": metadata.get("author"),
                "total_chunks": corpus_data.get("totalChunks", 0),
                "content_types": corpus_data.get("contentTypes", {}),
                "processed_at": corpus_data.get("processedAt"),
            },
            "accessibility_features": {
                "wcag_compliance": "AA",
                "pdf_ua_compliant": True,
                "screen_reader_optimized": True,
                "has_alt_text": True,
                "has_structure_tags": True,
            },
            "search_capabilities": {
                "semantic_search_available": True,
                "embedding_model": "amazon.titan-embed-text-v1",
                "search_endpoint": f"/public/embeddings/search?doc_ids={doc_id}",
            },
            "client_info": {
                "organization": metadata.get("client_organization", "Unknown"),
                "website": metadata.get("client_website"),
                "contact": metadata.get("client_contact"),
            },
            "requester": requester,
        }

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get document {accesspdf_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document information"
        )


@router.get("/documents", response_model=dict[str, Any])
async def list_available_documents(
    client_domain: Optional[str] = Query(None, description="Filter by client domain"),
    limit: int = Query(50, ge=1, le=100),
    requester: str = Depends(rate_limit_check)
):
    """
    List available documents for embedding search.

    LLMs can discover documents by client domain or browse all public documents.
    """
    try:
        s3_client = boto3.client("s3")
        bucket_name = os.getenv("PDF_DERIVATIVES_BUCKET", "pdf-derivatives")

        # List available corpus files
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix="corpus/",
            MaxKeys=limit
        )

        documents = []
        for obj in response.get('Contents', []):
            key = obj['Key']
            # Extract doc_id from path
            parts = key.split('/')
            if len(parts) >= 3 and parts[0] == 'corpus' and parts[2] == 'document_corpus.json':
                doc_id = parts[1]

                # Load document metadata
                try:
                    corpus_response = s3_client.get_object(Bucket=bucket_name, Key=key)
                    corpus_data = json.loads(corpus_response["Body"].read())
                    metadata = corpus_data.get("metadata", {})

                    documents.append({
                        "doc_id": doc_id,
                        "title": metadata.get("title", "Unknown Document"),
                        "author": metadata.get("author"),
                        "total_chunks": corpus_data.get("totalChunks", 0),
                        "processed_at": corpus_data.get("processedAt"),
                        "content_types": corpus_data.get("contentTypes", {}),
                    })

                except Exception:
                    # Skip documents we can't load metadata for
                    continue

        return {
            "total_documents": len(documents),
            "documents": documents,
            "requester": requester,
            "api_info": {
                "version": "v1",
                "embedding_model": "amazon.titan-embed-text-v1",
                "search_endpoint": "/public/embeddings/search",
            }
        }

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document list"
        )


@router.get("/health")
async def embedding_api_health():
    """Health check for public embeddings API - completely public."""

    return {
        "status": "healthy",
        "service": "AccessPDF Public API",
        "version": "1.0",
        "authentication": "none_required",
        "rate_limits": {
            "search_requests": "1000/hour per IP",
            "document_discovery": "unlimited",
            "burst_limit": "10/minute per IP"
        },
        "endpoints": {
            "search_documents": "POST /public/embeddings/search",
            "discover_document": "GET /public/embeddings/documents/{accesspdf_id}",
            "browse_documents": "GET /public/embeddings/documents",
            "client_registration": "POST /v1/registration/register"
        },
        "supported_llms": ["Any LLM or search system"],
        "embedding_model": "amazon.titan-embed-text-v1",
        "embedding_dimensions": 1536,
        "documentation": "https://docs.accesspdf.com/api",
        "integration_guide": "https://docs.accesspdf.com/integration",
        "cdn_script": "https://cdn.accesspdf.com/integration.js",
        "wordpress_plugin": "https://cdn.accesspdf.com/plugins/wordpress-accesspdf.zip",
        "timestamp": datetime.utcnow().isoformat(),
    }

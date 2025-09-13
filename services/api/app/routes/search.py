"""
Semantic search and retrieval endpoints for LLM-ready document corpus
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Optional

import boto3
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

# Add shared services to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../shared"))

from ..auth import User as UserInfo
from ..auth import get_current_user

router = APIRouter(prefix="/search", tags=["semantic_search"])


class SearchRequest(BaseModel):
    """Request model for semantic search."""

    query: str = Field(..., description="Search query text")
    doc_ids: Optional[list[str]] = Field(None, description="Limit search to specific documents")
    chunk_types: Optional[list[str]] = Field(None, description="Filter by chunk types")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of results")
    min_score: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity score")
    include_content: bool = Field(True, description="Include full chunk content")
    include_context: bool = Field(False, description="Include surrounding chunks")


class SearchResult(BaseModel):
    """Search result model."""

    chunk_id: str
    doc_id: str
    score: float
    content: Optional[str] = None
    content_preview: str
    metadata: dict[str, Any]
    context: Optional[dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Search response model."""

    query: str
    total_results: int
    processing_time_ms: float
    results: list[SearchResult]


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Perform semantic search across document corpus using embeddings.
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
                detail="Failed to generate embedding for query"
            )

        # Initialize S3 client
        s3_client = boto3.client("s3")
        bucket_name = os.getenv("PDF_DERIVATIVES_BUCKET", "pdf-derivatives")

        # Search across documents
        all_results = []

        # If specific doc_ids provided, search only those
        doc_ids_to_search = request.doc_ids

        # If no specific docs, get user's accessible documents
        if not doc_ids_to_search:
            # Get user's documents from MongoDB
            from services.shared.mongo.documents import get_document_repository
            doc_repo = get_document_repository()

            # Get documents owned by user (or all if admin)
            user_docs = doc_repo.find_documents_by_owner(
                owner_id=current_user.sub,
                limit=100  # Reasonable limit for search
            )
            doc_ids_to_search = [doc.get("docId") for doc in user_docs]

        # Search each document's embeddings
        for doc_id in doc_ids_to_search:
            embeddings_s3_key = f"embeddings/{doc_id}/titan_embeddings.json"

            try:
                # Load document embeddings
                embeddings_data = embeddings_service.load_embeddings_from_s3(
                    embeddings_s3_key,
                    bucket_name
                )

                if embeddings_data:
                    # Find similar chunks
                    similar_chunks = embeddings_service.find_similar_chunks(
                        query_embedding=query_embedding,
                        document_embeddings=embeddings_data,
                        top_k=request.limit,
                        min_similarity=request.min_score
                    )

                    all_results.extend(similar_chunks)

            except Exception as e:
                # Log error but continue with other documents
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not search document {doc_id}: {e}")
                continue

        # Sort all results by similarity score
        all_results.sort(key=lambda x: x["similarity"], reverse=True)

        # Limit results
        final_results = all_results[:request.limit]

        # Load full chunk data if requested
        search_results = []
        for result in final_results:
            chunk_id = result["chunkId"]
            doc_id = result["docId"]

            # Load chunk data if content requested
            chunk_content = None
            chunk_metadata = {}

            if request.include_content:
                # Load corpus to get full chunk data
                try:
                    corpus_s3_key = f"corpus/{doc_id}/document_corpus.json"
                    corpus_response = s3_client.get_object(Bucket=bucket_name, Key=corpus_s3_key)
                    corpus_data = json.loads(corpus_response["Body"].read())

                    # Find the chunk in the corpus
                    for chunk in corpus_data.get("chunks", []):
                        if chunk.get("id") == chunk_id:
                            chunk_content = chunk.get("content")
                            chunk_metadata = {
                                "type": chunk.get("type"),
                                "page": chunk.get("page"),
                                "sectionPath": chunk.get("sectionPath", []),
                                "boundingBox": chunk.get("boundingBox"),
                                "characterCount": chunk.get("characterCount"),
                                "wordCount": chunk.get("wordCount"),
                            }
                            break

                except Exception:
                    # Use preview if full content unavailable
                    chunk_content = result["contentPreview"]

            search_result = SearchResult(
                chunk_id=chunk_id,
                doc_id=doc_id,
                score=result["similarity"],
                content=chunk_content if request.include_content else None,
                content_preview=result["contentPreview"],
                metadata=chunk_metadata
            )

            search_results.append(search_result)

        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        response = SearchResponse(
            query=request.query,
            total_results=len(search_results),
            processing_time_ms=processing_time,
            results=search_results
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/documents/{doc_id}/chunks")
async def get_document_chunks(
    doc_id: str,
    page: Optional[int] = Query(None, description="Filter by page number"),
    chunk_type: Optional[str] = Query(None, description="Filter by chunk type"),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get chunks for a specific document.
    """
    try:
        # Check document access
        from services.shared.mongo.documents import get_document_repository
        doc_repo = get_document_repository()

        document = doc_repo.get_document(doc_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Check ownership (user can only access own docs unless admin)
        if document.get("ownerId") != current_user.sub and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        # Load corpus data
        s3_client = boto3.client("s3")
        bucket_name = os.getenv("PDF_DERIVATIVES_BUCKET", "pdf-derivatives")
        corpus_s3_key = f"corpus/{doc_id}/document_corpus.json"

        try:
            corpus_response = s3_client.get_object(Bucket=bucket_name, Key=corpus_s3_key)
            corpus_data = json.loads(corpus_response["Body"].read())
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document corpus not found"
            )

        # Filter chunks
        chunks = corpus_data.get("chunks", [])

        if page is not None:
            chunks = [c for c in chunks if c.get("page") == page]

        if chunk_type:
            chunks = [c for c in chunks if c.get("type") == chunk_type]

        return {
            "doc_id": doc_id,
            "total_chunks": len(chunks),
            "chunks": chunks
        }

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get document chunks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document chunks"
        )


@router.get("/documents/{doc_id}/chunks/{chunk_id}")
async def get_chunk_detail(
    doc_id: str,
    chunk_id: str,
    include_context: bool = Query(False, description="Include surrounding chunks"),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get detailed information for a specific chunk.
    """
    try:
        # Check document access (same as above)
        from services.shared.mongo.documents import get_document_repository
        doc_repo = get_document_repository()

        document = doc_repo.get_document(doc_id)
        if not document or (document.get("ownerId") != current_user.sub and current_user.role != "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        # Load corpus and find chunk
        s3_client = boto3.client("s3")
        bucket_name = os.getenv("PDF_DERIVATIVES_BUCKET", "pdf-derivatives")
        corpus_s3_key = f"corpus/{doc_id}/document_corpus.json"

        corpus_response = s3_client.get_object(Bucket=bucket_name, Key=corpus_s3_key)
        corpus_data = json.loads(corpus_response["Body"].read())

        # Find the specific chunk
        target_chunk = None
        chunk_index = None

        for i, chunk in enumerate(corpus_data.get("chunks", [])):
            if chunk.get("id") == chunk_id:
                target_chunk = chunk
                chunk_index = i
                break

        if not target_chunk:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chunk not found"
            )

        result = {
            "chunk": target_chunk,
            "context": None
        }

        # Add context if requested
        if include_context:
            chunks = corpus_data.get("chunks", [])
            context_before = []
            context_after = []

            # Get 2 chunks before and after
            for i in range(max(0, chunk_index - 2), chunk_index):
                context_before.append(chunks[i])

            for i in range(chunk_index + 1, min(len(chunks), chunk_index + 3)):
                context_after.append(chunks[i])

            result["context"] = {
                "before": context_before,
                "after": context_after
            }

        return result

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get chunk detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chunk details"
        )


class QARequest(BaseModel):
    """Request model for Q&A generation."""

    question: str = Field(..., description="Question to answer")
    doc_ids: Optional[list[str]] = Field(None, description="Limit search to specific documents")
    max_chunks: int = Field(5, ge=1, le=20, description="Maximum chunks to use for context")
    min_score: float = Field(0.6, ge=0.0, le=1.0, description="Minimum similarity score for context")
    include_citations: bool = Field(True, description="Include source citations")


class Citation(BaseModel):
    """Citation model for QA responses."""

    doc_id: str
    chunk_id: str
    title: Optional[str] = None
    author: Optional[str] = None
    page: int
    section_path: list[str]
    excerpt: str
    confidence: float


class QAResponse(BaseModel):
    """Q&A response model."""

    question: str
    answer: str
    confidence: float
    citations: list[Citation]
    processing_time_ms: float
    model_used: str
    tokens_used: Optional[int] = None


@router.post("/qa", response_model=QAResponse)
async def answer_question(
    request: QARequest,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Generate answers to questions using document corpus and Bedrock Claude.
    """
    start_time = datetime.utcnow()

    try:
        # First, perform semantic search to get relevant chunks
        search_request = SearchRequest(
            query=request.question,
            doc_ids=request.doc_ids,
            limit=request.max_chunks,
            min_score=request.min_score,
            include_content=True,
            include_context=False
        )

        # Reuse the semantic search function
        search_response = await semantic_search(search_request, current_user)

        if not search_response.results:
            return QAResponse(
                question=request.question,
                answer="I couldn't find relevant information in the available documents to answer your question.",
                confidence=0.0,
                citations=[],
                processing_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                model_used="N/A",
                tokens_used=0
            )

        # Prepare context from search results
        context_chunks = []
        citations = []

        for result in search_response.results:
            if result.content:
                context_chunks.append(f"[Document: {result.doc_id}]\n{result.content}")

                # Prepare citation
                citation = Citation(
                    doc_id=result.doc_id,
                    chunk_id=result.chunk_id,
                    page=result.metadata.get("page", 1),
                    section_path=result.metadata.get("sectionPath", []),
                    excerpt=result.content_preview,
                    confidence=result.score
                )
                citations.append(citation)

        # Generate answer using Bedrock Claude
        context_text = "\n\n---\n\n".join(context_chunks)

        # Prepare prompt for Claude
        prompt = f"""Based on the following document excerpts, please answer the user's question.

Be precise and helpful. If the information isn't sufficient to answer confidently, say so.
Include specific details from the documents when relevant.

Question: {request.question}

Document Context:
{context_text}

Please provide a clear, helpful answer based on the available information."""

        # Call Bedrock Claude
        bedrock_client = boto3.client("bedrock-runtime")

        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )

        # Parse response
        result = json.loads(response["body"].read())
        answer_text = result["content"][0]["text"]
        usage = result.get("usage", {})

        # Calculate confidence based on search results quality
        avg_similarity = sum(r.score for r in search_response.results) / len(search_response.results)
        answer_confidence = min(avg_similarity * 1.1, 1.0)  # Boost slightly, cap at 1.0

        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return QAResponse(
            question=request.question,
            answer=answer_text,
            confidence=answer_confidence,
            citations=citations if request.include_citations else [],
            processing_time_ms=processing_time,
            model_used="anthropic.claude-3-5-sonnet-20241022-v2:0",
            tokens_used=usage.get("total_tokens")
        )

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"QA generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Answer generation failed: {str(e)}"
        )

"""
Services module for business logic
"""

from .preview import preview_service

class AWSServiceError(Exception):
    """AWS service error exception"""
    pass

class DocumentService:
    """Placeholder document service"""
    
    async def generate_presigned_upload_url(
        self, 
        user_id: str, 
        filename: str, 
        content_type: str, 
        file_size: int
    ):
        """Generate a pre-signed S3 upload URL"""
        from datetime import datetime, timedelta
        from uuid import uuid4
        import boto3
        from botocore.config import Config
        from ..models import PreSignedUploadResponse
        from ..config import settings
        
        # Generate document ID
        doc_id = uuid4()
        s3_key = f"uploads/{user_id}/{doc_id}/{filename}"
        
        # Create S3 client with browser-accessible endpoint
        # Use localhost instead of localstack for browser access
        browser_endpoint = settings.aws_endpoint_url.replace('localstack:4566', 'localhost:4566')
        s3_config = Config(signature_version='s3v4')
        s3_client = boto3.client(
            's3',
            endpoint_url=browser_endpoint,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name='us-east-1',
            config=s3_config
        )
        
        # Generate presigned POST
        expires_in = 3600  # 1 hour
        conditions = [
            ["content-length-range", 1, file_size * 2],  # Allow some flexibility
        ]
        
        try:
            presigned_post = s3_client.generate_presigned_post(
                Bucket=settings.s3_bucket,
                Key=s3_key,
                Fields={
                    "Content-Type": content_type,
                },
                Conditions=conditions,
                ExpiresIn=expires_in
            )
            
            return PreSignedUploadResponse(
                upload_url=presigned_post["url"],
                fields=presigned_post["fields"],
                expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                s3_key=s3_key,
                doc_id=doc_id
            )
            
        except Exception as e:
            from . import AWSServiceError
            raise AWSServiceError(f"Failed to generate presigned URL: {e}")
    
    async def create_document_from_upload(
        self,
        user_id: str,
        doc_id,
        s3_key: str,
        filename: str,
        content_type: str,
        file_size: int,
        metadata: dict = None
    ):
        """Create a document record after successful upload"""
        from datetime import datetime
        from ..models import DocumentResponse, DocumentStatus
        from services.shared.mongo.documents import get_document_repository
        from ..celery_app import celery_app
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Create document record in MongoDB
        doc_repo = get_document_repository()
        
        document_data = {
            "docId": str(doc_id),
            "ownerId": user_id,
            "filename": filename,
            "contentType": content_type,
            "fileSize": file_size,
            "s3Key": s3_key,
            "status": DocumentStatus.PENDING.value,
            "metadata": metadata or {}
        }
        
        try:
            # Create document record using repository method
            result = doc_repo.create_document(document_data)
            
            if result:
                # Queue the document for processing
                try:
                    task = celery_app.send_task(
                        'worker.process_pdf',
                        args=[str(doc_id), s3_key, user_id],
                        queue='celery'
                    )
                    logger.info(f"Queued document {doc_id} for processing with task ID: {task.id}")
                except Exception as queue_error:
                    logger.error(f"Failed to queue document {doc_id}: {queue_error}")
                    # Continue even if queueing fails - document is still created
                
                # Return document response
                now = datetime.utcnow()
                return DocumentResponse(
                    doc_id=doc_id,
                    filename=filename,
                    status=DocumentStatus.PENDING,
                    created_at=now,
                    updated_at=now,
                    user_id=user_id,
                    metadata=metadata or {}
                )
            else:
                raise Exception("Failed to create document record")
                
        except Exception as e:
            from . import AWSServiceError
            raise AWSServiceError(f"Failed to create document record: {e}")
    
    async def get_document(self, doc_id: str, user_id: str = None):
        """Get a document by ID"""
        from datetime import datetime
        from ..models import DocumentResponse, DocumentStatus
        from services.shared.mongo.documents import get_document_repository
        
        try:
            # Get document from MongoDB
            doc_repo = get_document_repository()
            document_data = doc_repo.get_document(doc_id)
            
            if not document_data:
                return None
            
            # Convert MongoDB document to DocumentResponse
            return DocumentResponse(
                doc_id=document_data.get("docId"),
                filename=document_data.get("filename"),
                status=DocumentStatus(document_data.get("status", "pending")),
                created_at=document_data.get("createdAt", datetime.utcnow()),
                updated_at=document_data.get("updatedAt", datetime.utcnow()),
                completed_at=document_data.get("completedAt"),
                user_id=document_data.get("ownerId", ""),
                metadata=document_data.get("metadata", {}),
                error_message=document_data.get("errorMessage"),
                artifacts=document_data.get("artifacts", {})
            )
            
        except Exception as e:
            from . import AWSServiceError
            raise AWSServiceError(f"Failed to get document: {e}")
    
    async def list_user_documents(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        status_filter: str = None
    ):
        """List documents for a user with pagination"""
        from datetime import datetime
        from ..models import DocumentResponse, DocumentStatus
        from services.shared.mongo.documents import get_document_repository
        
        try:
            # Get documents from MongoDB
            doc_repo = get_document_repository()
            
            # Calculate page from skip/limit
            page = (skip // limit) + 1 if limit > 0 else 1
            
            # Get documents with pagination
            status_filter_list = [status_filter] if status_filter else None
            result = doc_repo.get_documents_by_owner(
                owner_id=user_id,
                status_filter=status_filter_list,
                page=page,
                limit=limit,
                sort_by="createdAt",
                sort_order="desc"
            )
            
            # Convert to DocumentResponse objects
            document_responses = []
            for doc_data in result.get("documents", []):
                document_responses.append(DocumentResponse(
                    doc_id=doc_data.get("docId"),
                    filename=doc_data.get("filename"),
                    status=DocumentStatus(doc_data.get("status", "pending")),
                    created_at=doc_data.get("createdAt", datetime.utcnow()),
                    updated_at=doc_data.get("updatedAt", datetime.utcnow()),
                    completed_at=doc_data.get("completedAt"),
                    user_id=doc_data.get("ownerId", ""),
                    metadata=doc_data.get("metadata", {}),
                    error_message=doc_data.get("errorMessage"),
                    artifacts=doc_data.get("artifacts", {})
                ))
            
            return document_responses, result.get("total", 0)
            
        except Exception as e:
            from . import AWSServiceError
            raise AWSServiceError(f"Failed to list documents: {e}")
    
    async def create_document(
        self,
        user_id: str,
        filename: str = None,
        source_url: str = None,
        metadata: dict = None,
        priority: bool = False,
        webhook_url: str = None,
    ):
        """Create a new document record"""
        from datetime import datetime
        from uuid import uuid4
        from ..models import DocumentResponse, DocumentStatus
        from services.shared.mongo.documents import get_document_repository
        
        try:
            # Generate document ID
            doc_id = str(uuid4())
            now = datetime.utcnow()

            # Create document record in MongoDB
            doc_repo = get_document_repository()
            
            document_data = {
                "docId": doc_id,
                "ownerId": user_id,
                "status": DocumentStatus.PENDING.value,
                "createdAt": now,
                "updatedAt": now,
                "metadata": metadata or {},
                "artifacts": {}
            }

            if filename:
                document_data["filename"] = filename
            if source_url:
                document_data["sourceUrl"] = source_url
            if webhook_url:
                document_data["webhookUrl"] = webhook_url

            # Create document record using repository method
            result = doc_repo.create_document(document_data)
            
            if result:
                # Queue the document for processing
                try:
                    from ..celery_app import celery_app
                    # For regular upload, we need to construct the S3 key
                    s3_key = f"uploads/{user_id}/{doc_id}/{filename}" if filename else None
                    
                    if s3_key:
                        task = celery_app.send_task(
                            'worker.process_pdf',
                            args=[str(doc_id), s3_key, user_id],
                            queue='celery'
                        )
                        logger.info(f"Queued document {doc_id} for processing with task ID: {task.id}")
                    else:
                        logger.warning(f"No S3 key available for document {doc_id}, skipping job queue")
                except Exception as queue_error:
                    logger.error(f"Failed to queue document {doc_id}: {queue_error}")
                    # Continue even if queueing fails - document is still created
                
                # Return document response
                return DocumentResponse(
                    doc_id=doc_id,
                    filename=filename,
                    status=DocumentStatus.PENDING,
                    created_at=now,
                    updated_at=now,
                    user_id=user_id,
                    metadata=metadata or {},
                    priority=priority,
                    webhook_url=webhook_url
                )
            else:
                raise Exception("Failed to create document record")
                
        except Exception as e:
            from . import AWSServiceError
            raise AWSServiceError(f"Failed to create document: {e}")
    
    async def generate_presigned_url(
        self,
        doc_id: str,
        document_type,
        expires_in: int = 3600
    ):
        """Generate a presigned URL for downloading a document artifact"""
        from datetime import datetime, timedelta
        import boto3
        from botocore.config import Config
        from ..config import settings
        from ..models import DocumentType
        from services.shared.mongo.documents import get_document_repository
        
        # Get document record to find actual S3 key for original file
        doc_repo = get_document_repository()
        document_data = doc_repo.get_document(doc_id)
        
        if not document_data:
            raise AWSServiceError(f"Document not found: {doc_id}")
        
        # Map document types to S3 keys
        s3_key_mappings = {
            DocumentType.PDF: document_data.get("s3Key"),  # Use actual S3 key from document record
            DocumentType.ACCESSIBLE_PDF: f"accessible/{doc_id}/accessible.pdf",
            DocumentType.PREVIEW: f"previews/{doc_id}/preview.png",
            DocumentType.HTML: f"exports/{doc_id}/document.html",
            DocumentType.TEXT: f"exports/{doc_id}/document.txt",
            DocumentType.JSON: f"exports/{doc_id}/document.json",
            DocumentType.CSV: f"exports/{doc_id}/data.csv",
            DocumentType.CSV_ZIP: f"exports/{doc_id}/data.zip",
            DocumentType.ANALYSIS: f"reports/{doc_id}/analysis.json"  # Fixed: should be .json not .pdf
        }
        
        # Get the S3 key for this document type
        s3_key = s3_key_mappings.get(document_type)
        if not s3_key:
            raise AWSServiceError(f"Invalid document type: {document_type}")
        
        # Map document types to content types
        content_type_mappings = {
            DocumentType.PDF: "application/pdf",
            DocumentType.ACCESSIBLE_PDF: "application/pdf",
            DocumentType.PREVIEW: "image/png",
            DocumentType.HTML: "text/html",
            DocumentType.TEXT: "text/plain",
            DocumentType.JSON: "application/json",
            DocumentType.CSV: "text/csv",
            DocumentType.CSV_ZIP: "application/zip",
            DocumentType.ANALYSIS: "application/pdf"
        }
        
        content_type = content_type_mappings.get(document_type, "application/octet-stream")
        
        # Generate filename for download
        file_extensions = {
            DocumentType.PDF: "pdf",
            DocumentType.ACCESSIBLE_PDF: "pdf",
            DocumentType.PREVIEW: "png",
            DocumentType.HTML: "html",
            DocumentType.TEXT: "txt",
            DocumentType.JSON: "json",
            DocumentType.CSV: "csv",
            DocumentType.CSV_ZIP: "zip",
            DocumentType.ANALYSIS: "pdf"
        }
        
        extension = file_extensions.get(document_type, "bin")
        filename = f"{document_type.value}_{doc_id[-8:]}.{extension}"
        
        try:
            # Create S3 client with browser-accessible endpoint
            browser_endpoint = settings.aws_endpoint_url.replace('localstack:4566', 'localhost:4566')
            s3_config = Config(signature_version='s3v4')
            s3_client = boto3.client(
                's3',
                endpoint_url=browser_endpoint,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name='us-east-1',
                config=s3_config
            )
            
            # Generate presigned URL for download
            download_url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.s3_bucket,
                    'Key': s3_key,
                    'ResponseContentDisposition': f'attachment; filename="{filename}"'
                },
                ExpiresIn=expires_in
            )
            
            return download_url, content_type, filename
            
        except Exception as e:
            raise AWSServiceError(f"Failed to generate download URL: {e}")

class ReportsService:
    """Placeholder reports service"""
    pass

class WebhookService:
    """Placeholder webhook service"""
    pass

document_service = DocumentService()
reports_service = ReportsService()
webhook_service = WebhookService()

__all__ = ["preview_service", "AWSServiceError", "document_service", "reports_service", "webhook_service"]
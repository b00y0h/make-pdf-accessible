"""
Security services for virus scanning and file validation
"""
import asyncio
import io
import socket
import struct
from datetime import datetime
from typing import Optional, BinaryIO

from aws_lambda_powertools import Logger
from fastapi import HTTPException, UploadFile
from fastapi import status

from .config import settings

logger = Logger()


class VirusScanError(Exception):
    """Exception raised when virus scanning fails"""
    pass


class VirusDetectedError(Exception):
    """Exception raised when a virus is detected"""
    def __init__(self, virus_name: str):
        self.virus_name = virus_name
        super().__init__(f"Virus detected: {virus_name}")


class SecurityService:
    """Service for file security validation including virus scanning"""
    
    def __init__(self):
        self.clamav_host = settings.clamav_host
        self.clamav_port = settings.clamav_port
        self.clamav_timeout = settings.clamav_timeout
        self.virus_scanning_enabled = settings.enable_virus_scanning
    
    async def scan_file_for_viruses(self, file_content: bytes) -> bool:
        """
        Scan file content for viruses using ClamAV
        
        Args:
            file_content: The file content as bytes
            
        Returns:
            True if file is clean, raises VirusDetectedError if virus found
            
        Raises:
            VirusDetectedError: If a virus is detected
            VirusScanError: If scanning fails
        """
        if not self.virus_scanning_enabled:
            logger.warning("Virus scanning is disabled, skipping scan")
            return True
            
        try:
            # Connect to ClamAV daemon
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.clamav_host, self.clamav_port),
                timeout=self.clamav_timeout
            )
            
            try:
                # Send INSTREAM command
                writer.write(b"zINSTREAM\0")
                await writer.drain()
                
                # Send file data in chunks with size prefix
                chunk_size = 4096
                for i in range(0, len(file_content), chunk_size):
                    chunk = file_content[i:i + chunk_size]
                    # Send chunk size (4 bytes, big endian) followed by chunk
                    writer.write(struct.pack('>I', len(chunk)))
                    writer.write(chunk)
                    await writer.drain()
                
                # Send zero-length chunk to indicate end of data
                writer.write(struct.pack('>I', 0))
                await writer.drain()
                
                # Read response
                response = await asyncio.wait_for(
                    reader.read(1024),
                    timeout=self.clamav_timeout
                )
                
                response_str = response.decode('utf-8').strip()
                logger.info(f"ClamAV scan result: {response_str}")
                
                if "FOUND" in response_str:
                    # Extract virus name from response
                    virus_name = response_str.split(":")[1].strip().replace(" FOUND", "")
                    raise VirusDetectedError(virus_name)
                elif "OK" in response_str:
                    return True
                else:
                    raise VirusScanError(f"Unexpected ClamAV response: {response_str}")
                    
            finally:
                writer.close()
                await writer.wait_closed()
                
        except VirusDetectedError:
            # Re-raise virus detection errors
            raise
        except asyncio.TimeoutError:
            raise VirusScanError("ClamAV scan timeout")
        except Exception as e:
            raise VirusScanError(f"ClamAV scan failed: {str(e)}")
    
    async def validate_file_signature(self, file_content: bytes, filename: str) -> bool:
        """
        Validate file signature matches the extension
        
        Args:
            file_content: The file content as bytes
            filename: The filename with extension
            
        Returns:
            True if file signature is valid
            
        Raises:
            HTTPException: If file signature doesn't match extension
        """
        if len(file_content) < 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is too small to validate"
            )
        
        # Get file extension
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        # Check file signatures (magic numbers)
        file_signatures = {
            'pdf': [b'%PDF'],
            'doc': [b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'],  # MS Office compound document
            'docx': [b'PK\x03\x04'],  # ZIP-based format
            'txt': []  # Text files don't have a specific signature
        }
        
        expected_signatures = file_signatures.get(extension, [])
        
        # Skip validation for text files
        if not expected_signatures:
            return True
        
        # Check if file starts with any expected signature
        for signature in expected_signatures:
            if file_content.startswith(signature):
                return True
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File signature doesn't match extension .{extension}"
        )
    
    def validate_pdf_content(self, file_content: bytes) -> bool:
        """
        Validate PDF content for potentially malicious elements
        
        Args:
            file_content: The PDF file content as bytes
            
        Returns:
            True if PDF appears safe
            
        Raises:
            HTTPException: If suspicious content is detected
        """
        try:
            # Convert to string for content analysis (only first 10KB for performance)
            content_str = file_content[:10240].decode('utf-8', errors='ignore').lower()
            
            # List of suspicious keywords/patterns in PDFs
            suspicious_patterns = [
                '/javascript',
                '/js',
                '/launch',
                '/embeddedobject',
                'openaction',
                'importdatafromat',
                'exportdataobject',
                'submitform',
                'mailto:',
                'shell32.dll',
                'kernel32.dll',
                'ntdll.dll'
            ]
            
            found_suspicious = []
            for pattern in suspicious_patterns:
                if pattern in content_str:
                    found_suspicious.append(pattern)
            
            if found_suspicious:
                logger.warning(f"Suspicious PDF content detected: {found_suspicious}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PDF contains potentially malicious content"
                )
            
            return True
            
        except UnicodeDecodeError:
            # If we can't decode the content, it might be binary data which is normal for PDFs
            logger.info("PDF content contains binary data, skipping text-based validation")
            return True
    
    async def validate_upload_file(self, file: UploadFile) -> bytes:
        """
        Comprehensive validation of uploaded file
        
        Args:
            file: The uploaded file
            
        Returns:
            File content as bytes if validation passes
            
        Raises:
            HTTPException: If validation fails
            VirusDetectedError: If virus is detected
        """
        # Read file content
        content = await file.read()
        
        # Reset file pointer for potential future reads
        file.file.seek(0)
        
        # Validate file size
        if len(content) > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {settings.max_file_size} bytes"
            )
        
        # Validate file signature
        await self.validate_file_signature(content, file.filename or "unknown")
        
        # PDF-specific validation
        if file.filename and file.filename.lower().endswith('.pdf'):
            self.validate_pdf_content(content)
        
        # Virus scan
        await self.scan_file_for_viruses(content)
        
        logger.info(
            f"File validation completed successfully",
            extra={
                "filename": file.filename,
                "size": len(content),
                "content_type": file.content_type
            }
        )
        
        return content
    
    async def validate_s3_file(self, s3_client, bucket: str, key: str) -> bool:
        """
        Validate a file stored in S3
        
        Args:
            s3_client: The S3 client instance
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            True if file is safe
            
        Raises:
            VirusDetectedError: If virus is detected
            VirusScanError: If scanning fails
        """
        try:
            # Download file from S3
            logger.info(f"Downloading file from S3 for security validation: s3://{bucket}/{key}")
            
            response = s3_client.get_object(Bucket=bucket, Key=key)
            file_content = response['Body'].read()
            
            # Extract filename from key
            filename = key.split('/')[-1] if '/' in key else key
            
            # Validate file signature
            await self.validate_file_signature(file_content, filename)
            
            # PDF-specific validation
            if filename.lower().endswith('.pdf'):
                self.validate_pdf_content(file_content)
            
            # Virus scan
            await self.scan_file_for_viruses(file_content)
            
            logger.info(
                f"S3 file security validation passed",
                extra={
                    "bucket": bucket,
                    "key": key,
                    "size": len(file_content)
                }
            )
            
            return True
            
        except VirusDetectedError:
            # Re-raise virus detection errors
            raise
        except Exception as e:
            raise VirusScanError(f"S3 file validation failed: {str(e)}")
    
    def validate_file_metadata(self, filename: str, content_type: str = None, metadata: dict = None) -> bool:
        """
        Validate file metadata for security
        
        Args:
            filename: The filename
            content_type: MIME content type
            metadata: Additional metadata
            
        Returns:
            True if metadata is valid
            
        Raises:
            HTTPException: If metadata validation fails
        """
        # Validate filename
        if not filename or len(filename) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename length"
            )
        
        # Check for path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename contains invalid characters"
            )
        
        # Check for suspicious extensions
        suspicious_extensions = ['.exe', '.bat', '.cmd', '.scr', '.com', '.pif', '.vbs', '.js']
        for ext in suspicious_extensions:
            if filename.lower().endswith(ext):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File type not allowed: {ext}"
                )
        
        # Validate content type if provided
        if content_type:
            allowed_content_types = [
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'text/plain'
            ]
            if content_type not in allowed_content_types:
                logger.warning(f"Suspicious content type: {content_type}")
        
        return True
    
    def audit_security_event(self, event_type: str, user_id: str, details: dict = None):
        """
        Log security events for auditing
        
        Args:
            event_type: Type of security event
            user_id: User ID associated with the event
            details: Additional event details
        """
        if not settings.enable_security_audit_logging:
            return
        
        audit_data = {
            "event_type": event_type,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
        
        logger.info(
            f"SECURITY_AUDIT: {event_type}",
            extra={
                "audit_event": audit_data,
                "security_audit": True
            }
        )
    
    async def validate_processing_request(self, user_id: str, org_id: str, file_info: dict) -> bool:
        """
        Validate a processing request for security
        
        Args:
            user_id: User requesting processing
            org_id: Organization ID
            file_info: Information about the file to process
            
        Returns:
            True if request is valid
        """
        try:
            # Log the processing request
            self.audit_security_event(
                "PROCESSING_REQUEST",
                user_id,
                {
                    "org_id": org_id,
                    "filename": file_info.get("filename"),
                    "size": file_info.get("size"),
                    "processing_isolation_enabled": settings.enable_processing_isolation
                }
            )
            
            # Check for excessive file sizes (beyond normal limits)
            max_size = file_info.get("size", 0)
            if max_size > settings.max_file_size * 2:  # Double the normal limit
                self.audit_security_event(
                    "SUSPICIOUS_FILE_SIZE",
                    user_id,
                    {"size": max_size, "limit": settings.max_file_size}
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File size exceeds security limits"
                )
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating processing request: {e}")
            return True  # Allow on error to avoid blocking legitimate requests


# Global security service instance
security_service = SecurityService()
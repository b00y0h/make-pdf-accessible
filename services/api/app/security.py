"""
Security services for virus scanning and file validation
"""

import asyncio
import os
import struct
import sys
import tempfile
from datetime import datetime

from aws_lambda_powertools import Logger
from fastapi import HTTPException, UploadFile, status

from .config import settings

try:
    import PyPDF2
    PDF_METADATA_EXTRACTION_AVAILABLE = True
except ImportError:
    PDF_METADATA_EXTRACTION_AVAILABLE = False
    PyPDF2 = None

# Add shared services to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../shared"))

try:
    from security_validation import ValidationResult, is_pdf_safe, validate_pdf_file

    PDF_VALIDATION_AVAILABLE = True
except ImportError:
    PDF_VALIDATION_AVAILABLE = False
    validate_pdf_file = None
    ValidationResult = None
    is_pdf_safe = None

try:
    from file_signature_validation import (
        FileSignatureValidator,
        validate_file_signature,
    )

    FILE_SIGNATURE_VALIDATION_AVAILABLE = True
except ImportError:
    FILE_SIGNATURE_VALIDATION_AVAILABLE = False
    validate_file_signature = None
    FileSignatureValidator = None

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
                timeout=self.clamav_timeout,
            )

            try:
                # Send INSTREAM command
                writer.write(b"zINSTREAM\0")
                await writer.drain()

                # Send file data in chunks with size prefix
                chunk_size = 4096
                for i in range(0, len(file_content), chunk_size):
                    chunk = file_content[i : i + chunk_size]
                    # Send chunk size (4 bytes, big endian) followed by chunk
                    writer.write(struct.pack(">I", len(chunk)))
                    writer.write(chunk)
                    await writer.drain()

                # Send zero-length chunk to indicate end of data
                writer.write(struct.pack(">I", 0))
                await writer.drain()

                # Read response
                response = await asyncio.wait_for(
                    reader.read(1024), timeout=self.clamav_timeout
                )

                response_str = response.decode("utf-8").strip()
                logger.info(f"ClamAV scan result: {response_str}")

                if "FOUND" in response_str:
                    # Extract virus name from response
                    virus_name = (
                        response_str.split(":")[1].strip().replace(" FOUND", "")
                    )
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
        Validate file signature matches the extension using comprehensive validation

        Args:
            file_content: The file content as bytes
            filename: The filename with extension

        Returns:
            True if file signature is valid

        Raises:
            HTTPException: If file signature doesn't match extension or is dangerous
        """
        if len(file_content) < 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is too small to validate",
            )

        # Get file extension
        extension = filename.lower().split(".")[-1] if "." in filename else ""

        # Use comprehensive file signature validation if available
        if FILE_SIGNATURE_VALIDATION_AVAILABLE:
            try:
                # Write content to temporary file for validation
                with tempfile.NamedTemporaryFile(
                    suffix=f".{extension}", delete=False
                ) as temp_file:
                    temp_file.write(file_content)
                    temp_file.flush()
                    temp_path = temp_file.name

                try:
                    # Perform comprehensive signature validation
                    validation_result = validate_file_signature(temp_path, extension)

                    # Log validation results
                    logger.info(
                        "File signature validation completed",
                        extra={
                            "file_name": filename,
                            "expected_type": extension,
                            "detected_type": validation_result.detected_type,
                            "is_valid": validation_result.is_valid,
                            "confidence": validation_result.confidence,
                            "issues_count": len(validation_result.issues),
                        },
                    )

                    # Handle validation results
                    if not validation_result.is_valid:
                        # Log security event for invalid signatures
                        self.audit_security_event(
                            "INVALID_FILE_SIGNATURE",
                            "system",
                            {
                                "file_name": filename,
                                "expected_type": extension,
                                "detected_type": validation_result.detected_type,
                                "issues": validation_result.issues,
                                "confidence": validation_result.confidence,
                            },
                        )

                        # Check if it's a dangerous file type
                        if any(
                            "dangerous" in issue.lower()
                            or "not allowed" in issue.lower()
                            for issue in validation_result.issues
                        ):
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Dangerous file type detected: {', '.join(validation_result.issues[:2])}",
                            )

                        # Check for file type spoofing
                        if (
                            validation_result.detected_type
                            and validation_result.detected_type != extension
                        ):
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"File type spoofing detected: file appears to be .{validation_result.detected_type} but has .{extension} extension",
                            )

                        # Other validation issues
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"File signature validation failed: {validation_result.issues[0] if validation_result.issues else 'Unknown error'}",
                        )

                    # Log suspicious patterns if detected but still valid
                    if validation_result.issues and validation_result.confidence < 1.0:
                        logger.warning(
                            "File signature validation passed with warnings",
                            extra={
                                "file_name": filename,
                                "issues": validation_result.issues,
                                "confidence": validation_result.confidence,
                            },
                        )

                        self.audit_security_event(
                            "SUSPICIOUS_FILE_SIGNATURE",
                            "system",
                            {
                                "file_name": filename,
                                "issues": validation_result.issues,
                                "confidence": validation_result.confidence,
                            },
                        )

                    return True

                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(temp_path)
                    except:
                        pass

            except HTTPException:
                # Re-raise HTTP exceptions
                raise
            except Exception as e:
                logger.error(f"Advanced file signature validation failed: {e}")
                # Fall back to basic validation on error
                return self._basic_file_signature_validation(
                    file_content, filename, extension
                )

        else:
            # Fall back to basic validation if advanced validation not available
            logger.warning(
                "Advanced file signature validation not available, using basic validation"
            )
            return self._basic_file_signature_validation(
                file_content, filename, extension
            )

    def _basic_file_signature_validation(
        self, file_content: bytes, filename: str, extension: str
    ) -> bool:
        """
        Basic file signature validation fallback method

        Args:
            file_content: The file content as bytes
            filename: The filename for logging
            extension: File extension

        Returns:
            True if basic validation passes
        """
        # Check file signatures (magic numbers)
        file_signatures = {
            "pdf": [b"%PDF"],
            "doc": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],  # MS Office compound document
            "docx": [b"PK\x03\x04"],  # ZIP-based format
            "txt": [],  # Text files don't have a specific signature
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
            detail=f"File signature doesn't match extension .{extension}",
        )

    def validate_pdf_content(
        self, file_content: bytes, filename: str = "unknown.pdf"
    ) -> bool:
        """
        Validate PDF content for potentially malicious elements using comprehensive validation

        Args:
            file_content: The PDF file content as bytes
            filename: The filename for logging purposes

        Returns:
            True if PDF appears safe

        Raises:
            HTTPException: If suspicious content is detected
        """
        # Use comprehensive PDF validation if available
        if PDF_VALIDATION_AVAILABLE:
            try:
                # Write content to temporary file for validation
                with tempfile.NamedTemporaryFile(
                    suffix=".pdf", delete=False
                ) as temp_file:
                    temp_file.write(file_content)
                    temp_file.flush()
                    temp_path = temp_file.name

                try:
                    # Perform comprehensive validation
                    validation_result = validate_pdf_file(temp_path)

                    # Log the validation results
                    logger.info(
                        "PDF security validation completed",
                        extra={
                            "file_name": filename,
                            "is_valid": validation_result.is_valid,
                            "threat_level": validation_result.threat_level,
                            "issues_count": len(validation_result.issues),
                        },
                    )

                    # Handle validation results based on threat level
                    if validation_result.threat_level == "dangerous":
                        # Log security event
                        self.audit_security_event(
                            "DANGEROUS_PDF_DETECTED",
                            "system",
                            {
                                "file_name": filename,
                                "issues": validation_result.issues,
                                "threat_level": validation_result.threat_level,
                            },
                        )

                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"PDF contains dangerous content: {', '.join(validation_result.issues[:3])}",
                        )

                    elif validation_result.threat_level == "suspicious":
                        # Log suspicious activity but allow with warning
                        logger.warning(
                            f"Suspicious PDF content detected in {filename}",
                            extra={
                                "issues": validation_result.issues,
                                "recommendations": validation_result.recommendations,
                            },
                        )

                        self.audit_security_event(
                            "SUSPICIOUS_PDF_DETECTED",
                            "system",
                            {
                                "file_name": filename,
                                "issues": validation_result.issues,
                                "threat_level": validation_result.threat_level,
                            },
                        )

                        # Allow processing but log the event
                        return True

                    else:
                        # File is safe
                        return True

                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(temp_path)
                    except:
                        pass

            except HTTPException:
                # Re-raise HTTP exceptions
                raise
            except Exception as e:
                logger.error(f"PDF validation failed with error: {e}")
                # Fall back to basic validation on error
                return self._basic_pdf_validation(file_content, filename)

        else:
            # Fall back to basic validation if comprehensive validation not available
            logger.warning(
                "Comprehensive PDF validation not available, using basic validation"
            )
            return self._basic_pdf_validation(file_content, filename)

    def _basic_pdf_validation(self, file_content: bytes, filename: str) -> bool:
        """
        Basic PDF validation fallback method

        Args:
            file_content: The PDF file content as bytes
            filename: The filename for logging

        Returns:
            True if basic validation passes
        """
        try:
            # Convert to string for content analysis (only first 10KB for performance)
            content_str = file_content[:10240].decode("utf-8", errors="ignore").lower()

            # List of suspicious keywords/patterns in PDFs
            suspicious_patterns = [
                "/javascript",
                "/js",
                "/launch",
                "/embeddedobject",
                "openaction",
                "importdatafromat",
                "exportdataobject",
                "submitform",
                "mailto:",
                "shell32.dll",
                "kernel32.dll",
                "ntdll.dll",
            ]

            found_suspicious = []
            for pattern in suspicious_patterns:
                if pattern in content_str:
                    found_suspicious.append(pattern)

            if found_suspicious:
                logger.warning(f"Suspicious PDF content detected: {found_suspicious}")

                self.audit_security_event(
                    "SUSPICIOUS_PDF_BASIC_VALIDATION",
                    "system",
                    {"file_name": filename, "patterns_found": found_suspicious},
                )

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PDF contains potentially malicious content",
                )

            return True

        except UnicodeDecodeError:
            # If we can't decode the content, it might be binary data which is normal for PDFs
            logger.info(
                "PDF content contains binary data, skipping text-based validation"
            )
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
                detail=f"File size exceeds maximum allowed size of {settings.max_file_size} bytes",
            )

        # Validate file signature
        await self.validate_file_signature(content, file.filename or "unknown")

        # PDF-specific validation with enhanced preflight checks
        pdf_metadata = None
        if file.filename and file.filename.lower().endswith(".pdf"):
            preflight_result = await self.validate_pdf_preflight(content, file.filename)
            pdf_metadata = preflight_result['metadata']

            # Log any warnings
            if preflight_result['warnings']:
                logger.info(
                    f"PDF preflight warnings for {file.filename}: {preflight_result['warnings']}"
                )

        # Virus scan
        await self.scan_file_for_viruses(content)

        # Include PDF metadata in logging if available
        log_extra = {
            "file_name": file.filename,
            "size": len(content),
            "content_type": file.content_type,
        }
        if pdf_metadata:
            log_extra.update({
                "page_count": pdf_metadata['page_count'],
                "is_encrypted": pdf_metadata['is_encrypted'],
                "has_forms": pdf_metadata['has_forms'],
                "has_javascript": pdf_metadata['has_javascript']
            })

        logger.info(
            "File validation completed successfully",
            extra=log_extra,
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
            logger.info(
                f"Downloading file from S3 for security validation: s3://{bucket}/{key}"
            )

            response = s3_client.get_object(Bucket=bucket, Key=key)
            file_content = response["Body"].read()

            # Extract filename from key
            filename = key.split("/")[-1] if "/" in key else key

            # Validate file signature
            await self.validate_file_signature(file_content, filename)

            # PDF-specific validation
            if filename.lower().endswith(".pdf"):
                self.validate_pdf_content(file_content, filename)

            # Virus scan
            await self.scan_file_for_viruses(file_content)

            logger.info(
                "S3 file security validation passed",
                extra={"bucket": bucket, "key": key, "size": len(file_content)},
            )

            return True

        except VirusDetectedError:
            # Re-raise virus detection errors
            raise
        except Exception as e:
            raise VirusScanError(f"S3 file validation failed: {str(e)}")

    def validate_file_metadata(
        self, filename: str, content_type: str = None, metadata: dict = None
    ) -> bool:
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
                detail="Invalid filename length",
            )

        # Check for path traversal attempts
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename contains invalid characters",
            )

        # Check for suspicious extensions
        suspicious_extensions = [
            ".exe",
            ".bat",
            ".cmd",
            ".scr",
            ".com",
            ".pif",
            ".vbs",
            ".js",
        ]
        for ext in suspicious_extensions:
            if filename.lower().endswith(ext):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File type not allowed: {ext}",
                )

        # Validate content type if provided
        if content_type:
            allowed_content_types = [
                "application/pdf",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/plain",
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
            "details": details or {},
        }

        logger.info(
            f"SECURITY_AUDIT: {event_type}",
            extra={"audit_event": audit_data, "security_audit": True},
        )

    async def validate_processing_request(
        self, user_id: str, org_id: str, file_info: dict
    ) -> bool:
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
                    "file_name": file_info.get("filename"),
                    "size": file_info.get("size"),
                    "processing_isolation_enabled": settings.enable_processing_isolation,
                },
            )

            # Check for excessive file sizes (beyond normal limits)
            max_size = file_info.get("size", 0)
            if max_size > settings.max_file_size * 2:  # Double the normal limit
                self.audit_security_event(
                    "SUSPICIOUS_FILE_SIZE",
                    user_id,
                    {"size": max_size, "limit": settings.max_file_size},
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File size exceeds security limits",
                )

            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating processing request: {e}")
            return True  # Allow on error to avoid blocking legitimate requests

    def extract_pdf_metadata(self, file_content: bytes, filename: str) -> dict:
        """
        Extract PDF metadata including page count and encryption status

        Args:
            file_content: The PDF file content as bytes
            filename: The filename for logging purposes

        Returns:
            Dictionary containing PDF metadata
        """
        metadata = {
            'page_count': 0,
            'is_encrypted': False,
            'title': None,
            'author': None,
            'subject': None,
            'creator': None,
            'producer': None,
            'creation_date': None,
            'modification_date': None,
            'pdf_version': None,
            'has_forms': False,
            'has_javascript': False,
        }

        if not PDF_METADATA_EXTRACTION_AVAILABLE:
            logger.warning("PyPDF2 not available, skipping PDF metadata extraction")
            return metadata

        try:
            # Write content to temporary file for PDF analysis
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file.flush()
                temp_path = temp_file.name

            try:
                with open(temp_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)

                    # Basic metadata
                    metadata['page_count'] = len(pdf_reader.pages)
                    metadata['is_encrypted'] = pdf_reader.is_encrypted

                    # PDF version
                    if hasattr(pdf_reader, 'pdf_header'):
                        metadata['pdf_version'] = pdf_reader.pdf_header

                    # Document info
                    if pdf_reader.metadata:
                        doc_info = pdf_reader.metadata
                        metadata['title'] = doc_info.get('/Title')
                        metadata['author'] = doc_info.get('/Author')
                        metadata['subject'] = doc_info.get('/Subject')
                        metadata['creator'] = doc_info.get('/Creator')
                        metadata['producer'] = doc_info.get('/Producer')
                        metadata['creation_date'] = doc_info.get('/CreationDate')
                        metadata['modification_date'] = doc_info.get('/ModDate')

                    # Check for forms and JavaScript
                    if hasattr(pdf_reader, 'trailer') and pdf_reader.trailer:
                        root = pdf_reader.trailer.get('/Root')
                        if root and '/AcroForm' in root:
                            metadata['has_forms'] = True

                        # Check for JavaScript in document
                        for page_num in range(len(pdf_reader.pages)):
                            page = pdf_reader.pages[page_num]
                            if '/JS' in str(page) or '/JavaScript' in str(page):
                                metadata['has_javascript'] = True
                                break

                    # Validate page count limits
                    if metadata['page_count'] > settings.max_pdf_pages if hasattr(settings, 'max_pdf_pages') else 1000:
                        self.audit_security_event(
                            "EXCESSIVE_PDF_PAGES",
                            "system",
                            {
                                "file_name": filename,
                                "page_count": metadata['page_count'],
                                "limit": getattr(settings, 'max_pdf_pages', 1000)
                            }
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"PDF has too many pages ({metadata['page_count']}). Maximum allowed: {getattr(settings, 'max_pdf_pages', 1000)}"
                        )

                    # Log if PDF is encrypted
                    if metadata['is_encrypted']:
                        logger.warning(f"Encrypted PDF uploaded: {filename}")
                        self.audit_security_event(
                            "ENCRYPTED_PDF_UPLOADED",
                            "system",
                            {
                                "file_name": filename,
                                "page_count": metadata['page_count']
                            }
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Encrypted PDFs are not supported. Please remove password protection before uploading."
                        )

                    # Log if PDF has JavaScript
                    if metadata['has_javascript']:
                        logger.warning(f"PDF with JavaScript detected: {filename}")
                        self.audit_security_event(
                            "PDF_WITH_JAVASCRIPT",
                            "system",
                            {
                                "file_name": filename,
                                "page_count": metadata['page_count']
                            }
                        )

                    logger.info(
                        "PDF metadata extracted successfully",
                        extra={
                            "file_name": filename,
                            "page_count": metadata['page_count'],
                            "is_encrypted": metadata['is_encrypted'],
                            "has_forms": metadata['has_forms'],
                            "has_javascript": metadata['has_javascript']
                        }
                    )

            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except:
                    pass

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"PDF metadata extraction failed: {e}")
            # Don't fail the entire validation for metadata extraction errors

        return metadata

    async def validate_pdf_preflight(self, file_content: bytes, filename: str) -> dict:
        """
        Enhanced PDF preflight validation including metadata extraction

        Args:
            file_content: The PDF file content as bytes
            filename: The filename for logging purposes

        Returns:
            Dictionary containing validation results and metadata
        """
        validation_result = {
            'is_valid': True,
            'metadata': {},
            'warnings': [],
            'errors': []
        }

        try:
            # Extract PDF metadata
            metadata = self.extract_pdf_metadata(file_content, filename)
            validation_result['metadata'] = metadata

            # Validate PDF content (existing security validation)
            self.validate_pdf_content(file_content, filename)

            # Additional preflight checks
            if metadata['page_count'] == 0:
                validation_result['errors'].append("PDF appears to have no pages")
                validation_result['is_valid'] = False

            if metadata['has_javascript']:
                validation_result['warnings'].append("PDF contains JavaScript which may not be accessible")

            if metadata['has_forms']:
                validation_result['warnings'].append("PDF contains forms which may require additional accessibility review")

            logger.info(
                "PDF preflight validation completed",
                extra={
                    "file_name": filename,
                    "is_valid": validation_result['is_valid'],
                    "page_count": metadata['page_count'],
                    "warnings_count": len(validation_result['warnings']),
                    "errors_count": len(validation_result['errors'])
                }
            )

        except HTTPException:
            # Re-raise HTTP exceptions (from encryption/page limit checks)
            raise
        except Exception as e:
            logger.error(f"PDF preflight validation failed: {e}")
            validation_result['errors'].append(f"Validation error: {str(e)}")
            validation_result['is_valid'] = False

        return validation_result


# Global security service instance
security_service = SecurityService()

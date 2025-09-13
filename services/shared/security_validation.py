"""
PDF Content Security Validation Module

This module provides comprehensive security validation for PDF files to prevent
malicious content from being processed by the PDF accessibility platform.
"""

import os
import re
from dataclasses import dataclass
from typing import Any, Optional

import magic

try:
    import PyPDF2
    from PyPDF2 import PdfReader
except ImportError:
    PyPDF2 = None
    PdfReader = None

try:
    import pikepdf
except ImportError:
    pikepdf = None


@dataclass
class ValidationResult:
    """Result of PDF security validation"""

    is_valid: bool
    threat_level: str  # "safe", "suspicious", "dangerous"
    issues: list[str]
    file_info: dict[str, Any]
    recommendations: list[str]


@dataclass
class PDFMetadata:
    """PDF metadata extracted during validation"""

    file_size: int
    page_count: int
    has_javascript: bool
    has_forms: bool
    has_embedded_files: bool
    has_encryption: bool
    pdf_version: str
    creation_date: Optional[str]
    modification_date: Optional[str]
    creator: Optional[str]
    producer: Optional[str]


class PDFSecurityValidator:
    """
    Comprehensive PDF security validator

    Performs multiple layers of validation:
    1. File signature validation
    2. Content structure analysis
    3. Malicious pattern detection
    4. Metadata inspection
    5. Size and complexity limits
    """

    # PDF file signatures (magic bytes)
    PDF_SIGNATURES = [
        b"%PDF-1.",  # Standard PDF signature
    ]

    # Suspicious patterns in PDF content
    SUSPICIOUS_PATTERNS = [
        rb"/JavaScript",
        rb"/JS",
        rb"/Launch",
        rb"/GoToR",
        rb"/GoToE",
        rb"/URI",
        rb"/SubmitForm",
        rb"/ImportData",
        rb"/Sound",
        rb"/Movie",
        rb"/EmbeddedFile",
        rb"/FileAttachment",
        rb"/Encrypt",
        rb"/XFA",
        rb"/RichMedia",
        rb"/3D",
        rb"/U3D",
    ]

    # Dangerous JavaScript patterns
    DANGEROUS_JS_PATTERNS = [
        rb"eval\s*\(",
        rb"unescape\s*\(",
        rb"String\.fromCharCode",
        rb"document\.write",
        rb"app\.launchURL",
        rb"this\.exportDataObject",
        rb"util\.printf",
        rb"app\.execDialog",
    ]

    # Maximum limits
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_PAGES = 1000
    MAX_EMBEDDED_FILES = 10
    MAX_FORM_FIELDS = 500

    def __init__(self):
        self.magic_mime = magic.Magic(mime=True) if magic else None

    def validate_pdf(self, file_path: str) -> ValidationResult:
        """
        Perform comprehensive PDF security validation

        Args:
            file_path: Path to the PDF file to validate

        Returns:
            ValidationResult with validation outcome and details
        """
        issues = []
        recommendations = []
        threat_level = "safe"
        file_info = {}

        try:
            # 1. Basic file validation
            file_size = os.path.getsize(file_path)
            file_info["file_size"] = file_size
            file_info["file_path"] = file_path

            if file_size > self.MAX_FILE_SIZE:
                issues.append(
                    f"File size exceeds maximum limit ({self.MAX_FILE_SIZE} bytes)"
                )
                threat_level = "dangerous"

            if file_size == 0:
                issues.append("File is empty")
                threat_level = "dangerous"

            # 2. File signature validation
            signature_valid = self._validate_file_signature(file_path)
            if not signature_valid:
                issues.append("Invalid PDF file signature")
                threat_level = "dangerous"

            # 3. MIME type validation
            if self.magic_mime:
                mime_type = self.magic_mime.from_file(file_path)
                file_info["mime_type"] = mime_type
                if mime_type != "application/pdf":
                    issues.append(f"Invalid MIME type: {mime_type}")
                    threat_level = "suspicious"

            # 4. Content analysis
            content_issues = self._analyze_pdf_content(file_path)
            if content_issues:
                issues.extend(content_issues)
                if any("javascript" in issue.lower() for issue in content_issues):
                    threat_level = "dangerous"
                elif threat_level == "safe":
                    threat_level = "suspicious"

            # 5. Metadata extraction and validation
            try:
                metadata = self._extract_pdf_metadata(file_path)
                if metadata:
                    file_info["metadata"] = metadata.__dict__
                    metadata_issues = self._validate_metadata(metadata)
                    if metadata_issues:
                        issues.extend(metadata_issues)
                        if threat_level == "safe":
                            threat_level = "suspicious"
            except Exception as e:
                issues.append(f"Failed to extract metadata: {str(e)}")
                if threat_level == "safe":
                    threat_level = "suspicious"

            # 6. Generate recommendations
            recommendations = self._generate_recommendations(issues, file_info)

            # Determine final validation result
            is_valid = threat_level != "dangerous" and len(issues) == 0

            return ValidationResult(
                is_valid=is_valid,
                threat_level=threat_level,
                issues=issues,
                file_info=file_info,
                recommendations=recommendations,
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                threat_level="dangerous",
                issues=[f"Validation failed with error: {str(e)}"],
                file_info=file_info,
                recommendations=["File appears to be corrupted or malicious"],
            )

    def _validate_file_signature(self, file_path: str) -> bool:
        """Validate PDF file signature (magic bytes)"""
        try:
            with open(file_path, "rb") as f:
                header = f.read(16)
                return any(header.startswith(sig) for sig in self.PDF_SIGNATURES)
        except Exception:
            return False

    def _analyze_pdf_content(self, file_path: str) -> list[str]:
        """Analyze PDF content for suspicious patterns"""
        issues = []

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            # Check for suspicious patterns
            for pattern in self.SUSPICIOUS_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    pattern_name = pattern.decode("utf-8", errors="ignore").strip("/")
                    issues.append(f"Suspicious pattern detected: {pattern_name}")

            # Check for dangerous JavaScript patterns
            for pattern in self.DANGEROUS_JS_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    issues.append("Potentially malicious JavaScript detected")
                    break

            # Check for excessive complexity
            object_count = content.count(b"obj")
            if object_count > 10000:
                issues.append(f"Excessive PDF object count: {object_count}")

            # Check for suspicious encoding
            if b"/ASCIIHexDecode" in content or b"/ASCII85Decode" in content:
                issues.append("Suspicious encoding filters detected")

            return issues

        except Exception as e:
            return [f"Content analysis failed: {str(e)}"]

    def _extract_pdf_metadata(self, file_path: str) -> Optional[PDFMetadata]:
        """Extract PDF metadata for analysis"""
        try:
            # Try pikepdf first (more robust)
            if pikepdf:
                return self._extract_metadata_pikepdf(file_path)
            # Fallback to PyPDF2
            elif PyPDF2:
                return self._extract_metadata_pypdf2(file_path)
            else:
                return None
        except Exception:
            return None

    def _extract_metadata_pikepdf(self, file_path: str) -> Optional[PDFMetadata]:
        """Extract metadata using pikepdf library"""
        try:
            with pikepdf.open(file_path) as pdf:
                metadata = PDFMetadata(
                    file_size=os.path.getsize(file_path),
                    page_count=len(pdf.pages),
                    has_javascript=False,
                    has_forms=False,
                    has_embedded_files=False,
                    has_encryption=pdf.is_encrypted,
                    pdf_version=str(pdf.pdf_version),
                    creation_date=None,
                    modification_date=None,
                    creator=None,
                    producer=None,
                )

                # Check for JavaScript
                for page in pdf.pages:
                    if "/JS" in str(page) or "/JavaScript" in str(page):
                        metadata.has_javascript = True
                        break

                # Check for forms
                if "/AcroForm" in str(pdf.Root):
                    metadata.has_forms = True

                # Check for embedded files
                if "/EmbeddedFiles" in str(pdf.Root):
                    metadata.has_embedded_files = True

                # Extract document info if available
                if pdf.docinfo:
                    info = pdf.docinfo
                    metadata.creation_date = str(info.get("/CreationDate", ""))
                    metadata.modification_date = str(info.get("/ModDate", ""))
                    metadata.creator = str(info.get("/Creator", ""))
                    metadata.producer = str(info.get("/Producer", ""))

                return metadata

        except Exception:
            return None

    def _extract_metadata_pypdf2(self, file_path: str) -> Optional[PDFMetadata]:
        """Extract metadata using PyPDF2 library (fallback)"""
        try:
            with open(file_path, "rb") as f:
                reader = PdfReader(f)

                metadata = PDFMetadata(
                    file_size=os.path.getsize(file_path),
                    page_count=len(reader.pages),
                    has_javascript=False,
                    has_forms=False,
                    has_embedded_files=False,
                    has_encryption=reader.is_encrypted,
                    pdf_version=reader.pdf_header,
                    creation_date=None,
                    modification_date=None,
                    creator=None,
                    producer=None,
                )

                # Extract document info
                if reader.metadata:
                    metadata.creation_date = str(
                        reader.metadata.get("/CreationDate", "")
                    )
                    metadata.modification_date = str(
                        reader.metadata.get("/ModDate", "")
                    )
                    metadata.creator = str(reader.metadata.get("/Creator", ""))
                    metadata.producer = str(reader.metadata.get("/Producer", ""))

                return metadata

        except Exception:
            return None

    def _validate_metadata(self, metadata: PDFMetadata) -> list[str]:
        """Validate PDF metadata for security issues"""
        issues = []

        if metadata.page_count > self.MAX_PAGES:
            issues.append(f"Excessive page count: {metadata.page_count}")

        if metadata.has_javascript:
            issues.append("JavaScript detected in PDF")

        if metadata.has_embedded_files:
            issues.append("Embedded files detected")

        if metadata.has_encryption:
            issues.append("Encrypted PDF detected")

        # Check for suspicious metadata values
        suspicious_fields = [metadata.creator, metadata.producer]
        for field in suspicious_fields:
            if field and any(char in field for char in ["<", ">", "%", "\x00"]):
                issues.append("Suspicious characters in metadata")
                break

        return issues

    def _generate_recommendations(
        self, issues: list[str], file_info: dict[str, Any]
    ) -> list[str]:
        """Generate security recommendations based on validation results"""
        recommendations = []

        if not issues:
            recommendations.append("File appears to be safe for processing")
            return recommendations

        if any("javascript" in issue.lower() for issue in issues):
            recommendations.append("Remove JavaScript before processing")
            recommendations.append("Scan with additional security tools")

        if any("embedded" in issue.lower() for issue in issues):
            recommendations.append("Extract and scan embedded files separately")

        if any("encryption" in issue.lower() for issue in issues):
            recommendations.append("Decrypt PDF using appropriate tools")

        if any("size" in issue.lower() or "page" in issue.lower() for issue in issues):
            recommendations.append("Consider file size and complexity limits")

        recommendations.append("Review file with security team before processing")

        return recommendations


# Global validator instance
pdf_validator = PDFSecurityValidator()


def validate_pdf_file(file_path: str) -> ValidationResult:
    """
    Convenience function to validate a PDF file

    Args:
        file_path: Path to the PDF file

    Returns:
        ValidationResult with security assessment
    """
    return pdf_validator.validate_pdf(file_path)


def is_pdf_safe(file_path: str) -> bool:
    """
    Quick check if a PDF file is safe for processing

    Args:
        file_path: Path to the PDF file

    Returns:
        True if the file is safe, False otherwise
    """
    result = validate_pdf_file(file_path)
    return result.is_valid and result.threat_level == "safe"


# Export commonly used items
__all__ = [
    "ValidationResult",
    "PDFMetadata",
    "PDFSecurityValidator",
    "pdf_validator",
    "validate_pdf_file",
    "is_pdf_safe",
]

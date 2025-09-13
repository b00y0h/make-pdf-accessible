"""
Advanced File Signature Validation Module

This module provides comprehensive file signature validation that goes beyond
simple extension checking to detect file type spoofing and malicious files.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FileSignature:
    """File signature definition"""

    extension: str
    mime_type: str
    signatures: list[bytes]
    description: str
    max_check_bytes: int = 512


@dataclass
class ValidationResult:
    """File signature validation result"""

    is_valid: bool
    detected_type: Optional[str]
    expected_type: str
    mime_type: Optional[str]
    issues: list[str]
    confidence: float  # 0.0 to 1.0


class FileSignatureValidator:
    """
    Advanced file signature validator that detects file type spoofing
    and validates files based on their actual content rather than extensions
    """

    # Comprehensive file signature database
    FILE_SIGNATURES = {
        # PDF files
        "pdf": FileSignature(
            extension="pdf",
            mime_type="application/pdf",
            signatures=[
                b"%PDF-1.0",
                b"%PDF-1.1",
                b"%PDF-1.2",
                b"%PDF-1.3",
                b"%PDF-1.4",
                b"%PDF-1.5",
                b"%PDF-1.6",
                b"%PDF-1.7",
                b"%PDF-2.0",
            ],
            description="Portable Document Format",
        ),
        # Microsoft Office documents
        "doc": FileSignature(
            extension="doc",
            mime_type="application/msword",
            signatures=[
                b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",  # OLE compound document
                b"\x0d\x44\x4f\x43",  # DOC file
                b"\xdb\xa5\x2d\x00",  # Word document
            ],
            description="Microsoft Word Document (Legacy)",
        ),
        "docx": FileSignature(
            extension="docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            signatures=[
                b"PK\x03\x04",  # ZIP-based format
            ],
            description="Microsoft Word Document (OpenXML)",
        ),
        "xls": FileSignature(
            extension="xls",
            mime_type="application/vnd.ms-excel",
            signatures=[
                b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",  # OLE compound document
                b"\x09\x08\x06\x00\x00\x00\x10\x00",  # Excel signature
            ],
            description="Microsoft Excel Spreadsheet (Legacy)",
        ),
        "xlsx": FileSignature(
            extension="xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            signatures=[
                b"PK\x03\x04",  # ZIP-based format
            ],
            description="Microsoft Excel Spreadsheet (OpenXML)",
        ),
        "ppt": FileSignature(
            extension="ppt",
            mime_type="application/vnd.ms-powerpoint",
            signatures=[
                b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",  # OLE compound document
            ],
            description="Microsoft PowerPoint Presentation (Legacy)",
        ),
        "pptx": FileSignature(
            extension="pptx",
            mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            signatures=[
                b"PK\x03\x04",  # ZIP-based format
            ],
            description="Microsoft PowerPoint Presentation (OpenXML)",
        ),
        # Text files
        "txt": FileSignature(
            extension="txt",
            mime_type="text/plain",
            signatures=[],  # Text files don't have specific signatures
            description="Plain Text File",
        ),
        "rtf": FileSignature(
            extension="rtf",
            mime_type="application/rtf",
            signatures=[
                b"{\\rtf1",  # RTF header
            ],
            description="Rich Text Format",
        ),
        # Images (for completeness)
        "jpg": FileSignature(
            extension="jpg",
            mime_type="image/jpeg",
            signatures=[
                b"\xff\xd8\xff",  # JPEG
            ],
            description="JPEG Image",
        ),
        "png": FileSignature(
            extension="png",
            mime_type="image/png",
            signatures=[
                b"\x89PNG\r\n\x1a\n",  # PNG
            ],
            description="PNG Image",
        ),
        "gif": FileSignature(
            extension="gif",
            mime_type="image/gif",
            signatures=[
                b"GIF87a",  # GIF87a
                b"GIF89a",  # GIF89a
            ],
            description="GIF Image",
        ),
        # Archive formats
        "zip": FileSignature(
            extension="zip",
            mime_type="application/zip",
            signatures=[
                b"PK\x03\x04",  # ZIP
                b"PK\x05\x06",  # Empty ZIP
                b"PK\x07\x08",  # Spanned ZIP
            ],
            description="ZIP Archive",
        ),
        "rar": FileSignature(
            extension="rar",
            mime_type="application/vnd.rar",
            signatures=[
                b"Rar!\x1a\x07\x00",  # RAR v1.5+
                b"Rar!\x1a\x07\x01\x00",  # RAR v5.0+
            ],
            description="RAR Archive",
        ),
        # Executable files (dangerous)
        "exe": FileSignature(
            extension="exe",
            mime_type="application/x-msdownload",
            signatures=[
                b"MZ",  # DOS/Windows executable
            ],
            description="Windows Executable",
        ),
        "dll": FileSignature(
            extension="dll",
            mime_type="application/x-msdownload",
            signatures=[
                b"MZ",  # Windows DLL
            ],
            description="Windows Dynamic Link Library",
        ),
        # Script files (potentially dangerous)
        "bat": FileSignature(
            extension="bat",
            mime_type="application/bat",
            signatures=[],  # Batch files are text-based
            description="Windows Batch File",
        ),
        "ps1": FileSignature(
            extension="ps1",
            mime_type="application/x-powershell",
            signatures=[],  # PowerShell scripts are text-based
            description="PowerShell Script",
        ),
    }

    # Dangerous file types that should never be allowed
    DANGEROUS_EXTENSIONS = {
        "exe",
        "bat",
        "cmd",
        "com",
        "scr",
        "pif",
        "vbs",
        "js",
        "jar",
        "app",
        "deb",
        "pkg",
        "rpm",
        "dmg",
        "iso",
        "msi",
        "dll",
        "sys",
        "ps1",
        "sh",
        "bash",
        "zsh",
        "csh",
        "fish",
    }

    # Suspicious patterns that might indicate embedded executables
    SUSPICIOUS_PATTERNS = [
        b"MZ",  # DOS/Windows executable header
        b"\x7fELF",  # Linux ELF executable
        b"\xca\xfe\xba\xbe",  # Java class file
        b"\xfe\xed\xfa\xce",  # Mach-O executable (macOS)
        b"\xce\xfa\xed\xfe",  # Mach-O executable (macOS, reverse)
    ]

    def __init__(self):
        self.magic_mime = None
        self.magic_type = None

        # Initialize python-magic if available
        try:
            import magic

            self.magic_mime = magic.Magic(mime=True)
            self.magic_type = magic.Magic()
        except:
            pass

    def validate_file_signature(
        self, file_path: str, expected_extension: str = None
    ) -> ValidationResult:
        """
        Validate file signature against expected type

        Args:
            file_path: Path to the file to validate
            expected_extension: Expected file extension (without dot)

        Returns:
            ValidationResult with validation details
        """
        issues = []

        try:
            # Get file info
            os.path.getsize(file_path)
            if expected_extension is None:
                expected_extension = Path(file_path).suffix.lower().lstrip(".")

            # Read file header for signature analysis
            with open(file_path, "rb") as f:
                header = f.read(1024)  # Read first 1KB

            if len(header) == 0:
                return ValidationResult(
                    is_valid=False,
                    detected_type=None,
                    expected_type=expected_extension,
                    mime_type=None,
                    issues=["File is empty"],
                    confidence=0.0,
                )

            # Check if extension is dangerous
            if expected_extension.lower() in self.DANGEROUS_EXTENSIONS:
                return ValidationResult(
                    is_valid=False,
                    detected_type=expected_extension,
                    expected_type=expected_extension,
                    mime_type=None,
                    issues=[f"Dangerous file type not allowed: .{expected_extension}"],
                    confidence=1.0,
                )

            # Get expected signature
            expected_sig = self.FILE_SIGNATURES.get(expected_extension.lower())
            if not expected_sig:
                issues.append(f"Unknown file type: .{expected_extension}")
                confidence = 0.5
            else:
                confidence = 1.0

            # Detect actual file type by signature
            detected_type = self._detect_file_type_by_signature(header)

            # Get MIME type using python-magic if available
            detected_mime = None
            if self.magic_mime:
                try:
                    detected_mime = self.magic_mime.from_file(file_path)
                except:
                    pass

            # Validate signature match
            if expected_sig and expected_sig.signatures:
                signature_match = any(
                    header.startswith(sig) for sig in expected_sig.signatures
                )

                if not signature_match:
                    issues.append(
                        f"File signature does not match .{expected_extension} format"
                    )
                    confidence *= 0.5

                    # Check if it matches a different known type
                    if detected_type and detected_type != expected_extension:
                        issues.append(
                            f"File appears to be .{detected_type} but has .{expected_extension} extension"
                        )
                        confidence *= 0.3

            # Check for suspicious embedded patterns
            suspicious_found = self._check_suspicious_patterns(header)
            if suspicious_found:
                issues.extend(suspicious_found)
                confidence *= 0.2

            # Validate MIME type if available
            if detected_mime and expected_sig:
                if detected_mime != expected_sig.mime_type:
                    # Some tolerance for similar MIME types
                    if not self._are_mime_types_compatible(
                        detected_mime, expected_sig.mime_type
                    ):
                        issues.append(
                            f"MIME type mismatch: detected {detected_mime}, expected {expected_sig.mime_type}"
                        )
                        confidence *= 0.7

            # Additional checks for specific file types
            additional_issues = self._perform_additional_checks(
                file_path, expected_extension, header
            )
            if additional_issues:
                issues.extend(additional_issues)
                confidence *= 0.8

            is_valid = len(issues) == 0 or (
                confidence > 0.7
                and not any("dangerous" in issue.lower() for issue in issues)
            )

            return ValidationResult(
                is_valid=is_valid,
                detected_type=detected_type,
                expected_type=expected_extension,
                mime_type=detected_mime,
                issues=issues,
                confidence=confidence,
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                detected_type=None,
                expected_type=expected_extension or "unknown",
                mime_type=None,
                issues=[f"Validation failed: {str(e)}"],
                confidence=0.0,
            )

    def _detect_file_type_by_signature(self, header: bytes) -> Optional[str]:
        """Detect file type by analyzing file signature"""
        for ext, sig_info in self.FILE_SIGNATURES.items():
            if sig_info.signatures:
                for signature in sig_info.signatures:
                    if header.startswith(signature):
                        return ext
        return None

    def _check_suspicious_patterns(self, content: bytes) -> list[str]:
        """Check for suspicious patterns that might indicate malicious content"""
        issues = []

        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern in content:
                issues.append("Suspicious executable pattern detected")
                break

        # Check for polyglot files (files that are valid in multiple formats)
        polyglot_indicators = [
            (b"%PDF", b"PK\x03\x04"),  # PDF + ZIP
            (b"%PDF", b"MZ"),  # PDF + Executable
            (b"PK\x03\x04", b"MZ"),  # ZIP + Executable
        ]

        for pattern1, pattern2 in polyglot_indicators:
            if pattern1 in content and pattern2 in content:
                issues.append("Polyglot file detected (multiple file formats)")
                break

        return issues

    def _are_mime_types_compatible(self, detected: str, expected: str) -> bool:
        """Check if MIME types are compatible (handle similar types)"""
        # Handle OpenXML formats that are ZIP-based
        zip_based_formats = [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ]

        if detected == "application/zip" and expected in zip_based_formats:
            return True

        # Handle text format variations
        if "text/" in detected and "text/" in expected:
            return True

        return detected == expected

    def _perform_additional_checks(
        self, file_path: str, extension: str, header: bytes
    ) -> list[str]:
        """Perform additional file-specific validation checks"""
        issues = []

        # ZIP-based format validation (Office documents)
        if extension.lower() in ["docx", "xlsx", "pptx"] and header.startswith(
            b"PK\x03\x04"
        ):
            issues.extend(self._validate_zip_based_office_file(file_path, extension))

        # PDF specific validation
        if extension.lower() == "pdf":
            issues.extend(self._validate_pdf_structure(header))

        return issues

    def _validate_zip_based_office_file(
        self, file_path: str, extension: str
    ) -> list[str]:
        """Validate ZIP-based Office files for proper structure"""
        issues = []

        try:
            import zipfile

            with zipfile.ZipFile(file_path, "r") as zip_file:
                file_list = zip_file.namelist()

                # Check for required Office document structure
                required_files = {
                    "docx": ["word/document.xml", "[Content_Types].xml"],
                    "xlsx": ["xl/workbook.xml", "[Content_Types].xml"],
                    "pptx": ["ppt/presentation.xml", "[Content_Types].xml"],
                }

                if extension in required_files:
                    for required_file in required_files[extension]:
                        if required_file not in file_list:
                            issues.append(
                                f"Missing required {extension.upper()} file: {required_file}"
                            )

                # Check for suspicious files in the archive
                suspicious_files = []
                for filename in file_list:
                    if any(
                        filename.lower().endswith(ext)
                        for ext in self.DANGEROUS_EXTENSIONS
                    ):
                        suspicious_files.append(filename)

                if suspicious_files:
                    issues.append(
                        f'Suspicious files found in archive: {", ".join(suspicious_files)}'
                    )

        except zipfile.BadZipFile:
            issues.append(
                f"File claims to be {extension.upper()} but is not a valid ZIP archive"
            )
        except Exception as e:
            issues.append(f"Failed to validate {extension.upper()} structure: {str(e)}")

        return issues

    def _validate_pdf_structure(self, header: bytes) -> list[str]:
        """Validate PDF file structure"""
        issues = []

        # Check PDF version
        if header.startswith(b"%PDF-"):
            version_line = header.split(b"\n")[0]
            try:
                version = version_line.decode("ascii")
                if "2." in version:
                    issues.append(
                        "PDF 2.0 format detected (newer standard, verify compatibility)"
                    )
            except:
                issues.append("Invalid PDF version header")

        return issues


# Global validator instance
file_signature_validator = FileSignatureValidator()


def validate_file_signature(
    file_path: str, expected_extension: str = None
) -> ValidationResult:
    """
    Convenience function to validate file signature

    Args:
        file_path: Path to file
        expected_extension: Expected extension (without dot)

    Returns:
        ValidationResult
    """
    return file_signature_validator.validate_file_signature(
        file_path, expected_extension
    )


def is_file_signature_valid(file_path: str, expected_extension: str = None) -> bool:
    """
    Quick check if file signature is valid

    Args:
        file_path: Path to file
        expected_extension: Expected extension (without dot)

    Returns:
        True if signature is valid
    """
    result = validate_file_signature(file_path, expected_extension)
    return result.is_valid


# Export commonly used items
__all__ = [
    "FileSignature",
    "ValidationResult",
    "FileSignatureValidator",
    "file_signature_validator",
    "validate_file_signature",
    "is_file_signature_valid",
]

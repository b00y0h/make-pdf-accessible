"""
Services module for business logic
"""

from .preview import preview_service

class AWSServiceError(Exception):
    """AWS service error exception"""
    pass

__all__ = ["preview_service", "AWSServiceError"]
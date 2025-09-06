# Lambda entry point
# For backwards compatibility
from app.main import app, lambda_handler

__all__ = ["lambda_handler", "app"]

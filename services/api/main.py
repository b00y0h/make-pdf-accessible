# Lambda entry point
from app.main import lambda_handler

# For backwards compatibility
from app.main import app

__all__ = ["lambda_handler", "app"]

from contextlib import asynccontextmanager
from typing import Dict
import base64

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder, ENCODERS_BY_TYPE
from mangum import Mangum
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings
from .middleware import APIKeyAuthMiddleware
from .models import ErrorResponse, HealthResponse
from .routes import admin, api_keys, auth, demo, documents, quotas, reports, webhooks, search, embeddings, feedback, client, registration
from .services import AWSServiceError

# Initialize Powertools
logger = Logger(service=settings.powertools_service_name)
tracer = Tracer(service=settings.powertools_service_name)
metrics = Metrics(
    namespace=settings.powertools_metrics_namespace,
    service=settings.powertools_service_name,
)


def safe_bytes_encoder(obj):
    """
    Safe bytes encoder that handles binary data properly.
    
    Instead of trying to decode bytes as UTF-8 (which fails for binary PDF data),
    we encode them as base64 strings with a prefix to indicate the encoding type.
    """
    try:
        # Try to decode as UTF-8 first for text data
        return obj.decode('utf-8')
    except UnicodeDecodeError:
        # If it's binary data (like PDF), encode as base64
        return f"<base64>{base64.b64encode(obj).decode('ascii')}"


# Override FastAPI's default bytes encoder
ENCODERS_BY_TYPE[bytes] = safe_bytes_encoder


class CORSErrorMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure CORS headers are present even on error responses"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
        except Exception as exc:
            # Create error response
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
            # Log the actual error
            logger.error(f"Unhandled error: {exc}")
        
        # Add CORS headers if not present
        origin = request.headers.get("origin")
        if origin and origin in (settings.cors_origins or ["*"]):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
        elif not settings.cors_origins or "*" in settings.cors_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
            
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting PDF Accessibility API")
    yield
    # Shutdown
    logger.info("Shutting down PDF Accessibility API")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    debug=settings.debug,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Health check and service status endpoints"},
        {
            "name": "documents",
            "description": "Document upload, processing, and management",
        },
        {"name": "webhooks", "description": "Webhook endpoints for external callbacks"},
        {"name": "reports", "description": "Analytics and reporting endpoints"},
        {"name": "auth", "description": "Authentication and user profile endpoints"},
        {"name": "quotas", "description": "Tenant quota management and monitoring"},
        {"name": "API Keys", "description": "API key generation and management"},
        {"name": "admin", "description": "Admin-only endpoints for user management"},
    ],
)

# Add middlewares in reverse order (last added is executed first)

# 1. Add our custom CORS error middleware (executed last, ensures headers on all responses)
app.add_middleware(CORSErrorMiddleware)

# 2. Add standard CORS middleware for proper CORS handling
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if settings.cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 3. Add API Key authentication middleware (executed first)
app.add_middleware(
    APIKeyAuthMiddleware,
    excluded_paths=[
        "/docs",
        "/openapi.json", 
        "/health",
        "/ping",
        "/auth",  # BetterAuth endpoints
        "/documents",  # Dashboard and demo endpoints
        "/v1/documents",  # Versioned dashboard endpoints
        "/reports",  # Dashboard analytics
        "/v1/reports",  # Versioned dashboard analytics
    ],
)


# Custom exception handlers
@app.exception_handler(UnicodeDecodeError)
async def unicode_decode_error_handler(
    request: Request, exc: UnicodeDecodeError
) -> JSONResponse:
    """Handle UnicodeDecodeError in request validation"""
    logger.error(f"UnicodeDecodeError in request validation: {exc}")

    # This typically happens when binary data (like PDF content) gets included
    # in validation error messages and FastAPI tries to decode it as UTF-8
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error="validation_error",
            message="Invalid file content or encoding in request",
            details={"error": "Binary content cannot be processed in request validation"},
            request_id=getattr(request.state, "request_id", None),
        ).model_dump(),
    )


@app.exception_handler(AWSServiceError)
async def aws_service_exception_handler(
    request: Request, exc: AWSServiceError
) -> JSONResponse:
    """Handle AWS service errors"""
    logger.error(f"AWS service error: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="service_error",
            message="Internal service error",
            details={"service": "aws"},
        ).model_dump(),
    )


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Custom HTTP exception handler with structured error response"""

    # Log the error
    logger.error(
        f"HTTP exception: {exc.status_code}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method,
        },
    )

    # Increment error metrics
    metrics.add_metric(name="HTTPErrors", unit="Count", value=1)
    metrics.add_metric(name=f"HTTPErrors{exc.status_code}", unit="Count", value=1)

    error_response = ErrorResponse(
        error=f"http_{exc.status_code}",
        message=exc.detail if isinstance(exc.detail, str) else "HTTP error",
        details=exc.detail if isinstance(exc.detail, dict) else None,
        request_id=getattr(request.state, "request_id", None),
    )

    return JSONResponse(
        status_code=exc.status_code, content=error_response.model_dump()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unexpected errors"""

    logger.exception(f"Unexpected error: {exc}")
    metrics.add_metric(name="UnexpectedErrors", unit="Count", value=1)

    error_response = ErrorResponse(
        error="internal_error",
        message="Internal server error",
        request_id=getattr(request.state, "request_id", None),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


# Middleware for request tracing
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID for request tracing"""
    import uuid

    correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    request.state.request_id = correlation_id

    # Add to Powertools context
    logger.set_correlation_id(correlation_id)

    response = await call_next(request)
    response.headers["x-correlation-id"] = correlation_id

    return response


# Health check endpoint
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Service health check",
    description="Get service health status and version information.",
)
@tracer.capture_method
async def health_check() -> HealthResponse:
    """Service health check"""

    # Check dependencies
    dependencies = {}

    try:
        # Test AWS connectivity (simplified check)
        import boto3

        sts = boto3.client("sts", region_name=settings.aws_region)
        sts.get_caller_identity()
        dependencies["aws"] = "healthy"
    except Exception as e:
        logger.error(f"AWS health check failed: {e}")
        dependencies["aws"] = "unhealthy"

    # Determine overall status
    overall_status = (
        "healthy"
        if all(status == "healthy" for status in dependencies.values())
        else "degraded"
    )

    metrics.add_metric(name="HealthChecks", unit="Count", value=1)

    return HealthResponse(
        status=overall_status, version=settings.api_version, dependencies=dependencies
    )


# Root endpoint
@app.get(
    "/",
    tags=["health"],
    summary="API root",
    description="API root endpoint with basic information.",
)
async def root() -> Dict[str, str]:
    """API root endpoint"""
    return {
        "service": settings.api_title,
        "version": settings.api_version,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


# Include routers with versioning
app.include_router(auth.router, prefix="/v1")
app.include_router(documents.router, prefix="/v1")
app.include_router(demo.router, prefix="/v1")
app.include_router(webhooks.router, prefix="/v1")
app.include_router(reports.router, prefix="/v1")
app.include_router(quotas.router, prefix="/v1")
app.include_router(api_keys.router, prefix="/v1")
app.include_router(admin.router, prefix="/v1")
app.include_router(search.router, prefix="/v1")
app.include_router(feedback.router)
app.include_router(client.router)
app.include_router(registration.router)
app.include_router(embeddings.router)  # No versioning for public API

# Legacy routes (maintain backward compatibility)
app.include_router(auth.router, tags=["legacy"])
app.include_router(documents.router, tags=["legacy"])
app.include_router(demo.router, tags=["legacy"])


# Lambda handler
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """Lambda handler with Powertools integration"""

    # Log incoming event (excluding sensitive data)
    safe_event = {k: v for k, v in event.items() if k not in ["headers", "body"]}
    logger.info("Lambda invocation", extra={"event": safe_event})

    # Create Mangum handler
    handler = Mangum(app, lifespan="off")

    try:
        response = handler(event, context)

        # Log response status
        logger.info(
            "Lambda response",
            extra={"status_code": response.get("statusCode", "unknown")},
        )

        return response

    except Exception as e:
        logger.exception(f"Lambda handler error: {e}")
        metrics.add_metric(name="LambdaErrors", unit="Count", value=1)

        # Return error response
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": '{"error": "internal_error", "message": "Lambda execution failed"}',
        }


# For local development
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

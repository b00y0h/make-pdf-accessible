from contextlib import asynccontextmanager
from typing import Dict

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings
from .middleware import APIKeyAuthMiddleware
from .models import ErrorResponse, HealthResponse
from .routes import admin, api_keys, auth, demo, documents, quotas, reports, webhooks
from .services import AWSServiceError

# Initialize Powertools
logger = Logger(service=settings.powertools_service_name)
tracer = Tracer(service=settings.powertools_service_name)
metrics = Metrics(
    namespace=settings.powertools_metrics_namespace,
    service=settings.powertools_service_name,
)


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
        "/documents",  # Temporarily excluded for demo
    ],
)


# Custom exception handlers
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


# Include routers
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(demo.router)
app.include_router(webhooks.router)
app.include_router(reports.router)
app.include_router(quotas.router)
app.include_router(api_keys.router)
app.include_router(admin.router)


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

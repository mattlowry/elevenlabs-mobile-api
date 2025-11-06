"""
ElevenLabs MCP SSE Server for Cloud Deployment

This server wraps the ElevenLabs MCP server in an SSE (Server-Sent Events) transport
layer using FastMCP's built-in SSE support, making it deployable on cloud platforms
like Render.

Features:
- SSE transport for remote MCP access via FastMCP
- Session management with Mcp-Session-Id headers
- Origin validation for security
- Health check endpoint
- CORS support for web clients
- Environment-based configuration
- Production-ready error handling
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.applications import Starlette
from starlette.routing import Mount

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost,http://localhost:3000,http://127.0.0.1").split(",")

# Validate required environment variables
required_env_vars = ["ELEVENLABS_API_KEY"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

logger.info("Starting ElevenLabs MCP SSE Server")
logger.info(f"Server will listen on {HOST}:{PORT}")
logger.info(f"Allowed origins: {ALLOWED_ORIGINS}")


# Import MCP server after environment is loaded
from elevenlabs_mcp.server import mcp

# Configure MCP server for SSE
mcp.settings.mount_path = "/sse"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application."""
    logger.info("Server starting up...")
    logger.info(f"ElevenLabs API Key configured: {bool(os.getenv('ELEVENLABS_API_KEY'))}")
    yield
    logger.info("Server shutting down...")


# Create main FastAPI application for health checks and info
main_app = FastAPI(
    title="ElevenLabs MCP SSE Server",
    description="Server-Sent Events transport for ElevenLabs MCP",
    version="1.0.0",
    lifespan=lifespan
)


# Origin validation middleware for security
@main_app.middleware("http")
async def validate_origin(request: Request, call_next):
    """
    Validate Origin header to prevent DNS rebinding attacks.
    Required by MCP specification for security.
    """
    # Skip validation for health check and root
    if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
        return await call_next(request)

    origin = request.headers.get("origin")
    host = request.headers.get("host", "").split(":")[0]

    # Allow requests from localhost/127.0.0.1
    if host in ["localhost", "127.0.0.1"]:
        response = await call_next(request)
        return response

    # Validate origin if present
    if origin:
        # Check if origin is in allowed list
        origin_allowed = any(
            origin.startswith(allowed) for allowed in ALLOWED_ORIGINS
        )

        if not origin_allowed:
            logger.warning(f"Rejected request from unauthorized origin: {origin}")
            return Response(
                content="Unauthorized origin",
                status_code=status.HTTP_403_FORBIDDEN
            )

    response = await call_next(request)
    return response


# Add CORS middleware
main_app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)


@main_app.get("/")
async def root():
    """Root endpoint with server information."""
    return {
        "name": "ElevenLabs MCP SSE Server",
        "version": "1.0.0",
        "status": "running",
        "transport": "sse",
        "mcp_version": "2025-03-26",
        "endpoints": {
            "health": "/health",
            "sse": "/sse",
            "docs": "/docs"
        },
        "info": "FastMCP-based SSE server for ElevenLabs API"
    }


@main_app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Check if API key is configured
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            return Response(
                content='{"status": "unhealthy", "reason": "ELEVENLABS_API_KEY not configured"}',
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                media_type="application/json"
            )

        return {
            "status": "healthy",
            "server": "ElevenLabs MCP SSE",
            "transport": "sse",
            "mcp_version": "2025-03-26",
            "api_configured": True
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return Response(
            content=f'{{"status": "unhealthy", "error": "{str(e)}"}}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )


# Create Starlette app that mounts the MCP SSE server
app = Starlette(
    routes=[
        Mount("/sse", app=mcp.sse_app()),
        Mount("/", app=main_app),
    ]
)


# Development server runner
if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting development server on {HOST}:{PORT}")
    logger.info("SSE endpoint available at: /sse")
    logger.info("Health check available at: /health")

    uvicorn.run(
        "sse_server:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info",
        access_log=True
    )

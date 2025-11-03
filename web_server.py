"""
FastAPI wrapper for ElevenLabs MCP Server
This allows the MCP server to be deployed as a web service on platforms like Render.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="ElevenLabs MCP Server API",
    description="Web API wrapper for ElevenLabs MCP Server",
    version="0.9.0"
)


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "status": "running",
        "service": "ElevenLabs MCP Server",
        "version": "0.9.0",
        "note": "This is a web wrapper for the MCP server. Use the /health endpoint for health checks."
    }


@app.get("/health")
async def health():
    """Health check endpoint for Render"""
    api_key = os.getenv("ELEVENLABS_API_KEY")

    return {
        "status": "healthy",
        "api_key_configured": bool(api_key and api_key != "your_api_key_here"),
        "environment": {
            "base_path": os.getenv("ELEVENLABS_MCP_BASE_PATH", "~/Desktop"),
            "output_mode": os.getenv("ELEVENLABS_MCP_OUTPUT_MODE", "files"),
            "residency": os.getenv("ELEVENLABS_API_RESIDENCY", "us")
        }
    }


@app.get("/api/info")
async def api_info():
    """Get API information"""
    return {
        "message": "ElevenLabs MCP Server Web API",
        "documentation": "/docs",
        "health_check": "/health",
        "note": "This server provides a web interface to the ElevenLabs MCP functionality"
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

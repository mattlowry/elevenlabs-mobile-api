#!/bin/bash
# Quick Start Script for ElevenLabs MCP SSE Server

set -e

echo "=========================================="
echo "ElevenLabs MCP SSE Server - Quick Start"
echo "=========================================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Python $PYTHON_VERSION detected"

# Check for API key
if [ -z "$ELEVENLABS_API_KEY" ]; then
    echo ""
    echo "Error: ELEVENLABS_API_KEY environment variable not set"
    echo ""
    echo "Please set your API key:"
    echo "  export ELEVENLABS_API_KEY='your_api_key_here'"
    echo ""
    echo "Get your API key at: https://elevenlabs.io/app/settings/api-keys"
    exit 1
fi

echo "✓ API key configured"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip3 install -q -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Run the server
echo "Starting SSE server..."
echo ""
echo "Server will be available at:"
echo "  - Health check: http://localhost:8000/health"
echo "  - SSE endpoint: http://localhost:8000/sse"
echo "  - API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 sse_server.py

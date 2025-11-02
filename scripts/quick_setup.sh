#!/bin/bash

# ElevenLabs MCP Server Quick Setup Script
# This script sets up the environment and API key for immediate use

echo "🎙️ ElevenLabs MCP Server Setup"
echo "==============================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "✅ .env file created!"
fi

# Load the API key from .env
source .env

# Verify API key is set
if [ -z "$ELEVENLABS_API_KEY" ] || [ "$ELEVENLABS_API_KEY" = "PUT_YOUR_KEY_HERE" ]; then
    echo "❌ API key not set! Please update .env file with your ElevenLabs API key."
    exit 1
fi

echo "✅ API key loaded from .env file"
echo "🔑 API Key: ${ELEVENLABS_API_KEY:0:10}..."

# Export environment variable for current session
export ELEVENLABS_API_KEY

echo ""
echo "🚀 Setup complete! You can now:"
echo "1. Run the demo: python examples/conversational_agent_demo.py"
echo "2. Start the MCP server: python -m elevenlabs_mcp.server"
echo "3. Configure your MCP client using the examples in CONFIGURATION.md"
echo ""
echo "For Claude Desktop integration, see CONFIGURATION.md for the full configuration."
#!/usr/bin/env python3
"""
ElevenLabs MCP Server Quick Setup
Sets up the environment and verifies API key configuration
"""

import os
import sys
from pathlib import Path

def main():
    print("🎙️ ElevenLabs MCP Server Setup")
    print("=" * 35)
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        print("Creating .env file from .env.example...")
        example_file = Path(".env.example")
        if example_file.exists():
            with open(example_file, 'r') as src, open(env_file, 'w') as dst:
                dst.write(src.read())
            print("✅ .env file created!")
        else:
            print("❌ .env.example file not found!")
            return 1
    else:
        print("✅ .env file found")
    
    # Load environment variables from .env file
    env_vars = {}
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    
    # Check API key
    api_key = env_vars.get('ELEVENLABS_API_KEY')
    if not api_key or api_key == 'PUT_YOUR_KEY_HERE':
        print("❌ API key not set! Please update .env file with your ElevenLabs API key.")
        return 1
    
    print(f"✅ API key loaded from .env file")
    print(f"🔑 API Key: {api_key[:10]}...")
    
    # Set environment variable for current session
    os.environ['ELEVENLABS_API_KEY'] = api_key
    
    print("")
    print("🚀 Setup complete! You can now:")
    print("1. Run the demo: python examples/conversational_agent_demo.py")
    print("2. Start the MCP server: python -m elevenlabs_mcp.server")
    print("3. Configure your MCP client using the examples in CONFIGURATION.md")
    print("")
    print("For Claude Desktop integration, see CONFIGURATION.md for the full configuration.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
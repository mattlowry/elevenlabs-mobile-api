#!/usr/bin/env python3
"""
Test client for ElevenLabs MCP SSE Server

This script tests the SSE connection to verify the server is working correctly.
"""

import asyncio
import json
import sys
from typing import Optional

try:
    import httpx
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.sse import sse_client
except ImportError:
    print("Error: Required packages not installed.")
    print("Install with: pip install mcp httpx")
    sys.exit(1)


async def test_sse_connection(server_url: str = "http://localhost:8000/sse"):
    """Test SSE connection to MCP server."""
    print(f"Testing connection to: {server_url}")
    print("-" * 60)

    try:
        # Test health endpoint first
        async with httpx.AsyncClient() as client:
            print("1. Testing health endpoint...")
            response = await client.get(f"{server_url.replace('/sse', '/health')}")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
            print()

        # Connect to SSE endpoint
        print("2. Connecting to SSE endpoint...")
        async with sse_client(server_url) as (read, write):
            async with ClientSession(read, write) as session:
                print("   ✓ Connected successfully!")
                print()

                # Initialize the session
                print("3. Initializing MCP session...")
                await session.initialize()
                print("   ✓ Session initialized!")
                print()

                # List available tools
                print("4. Listing available tools...")
                tools_result = await session.list_tools()
                print(f"   Found {len(tools_result.tools)} tools:")
                for i, tool in enumerate(tools_result.tools[:5], 1):
                    print(f"   {i}. {tool.name}")
                if len(tools_result.tools) > 5:
                    print(f"   ... and {len(tools_result.tools) - 5} more")
                print()

                # List available resources
                print("5. Listing available resources...")
                try:
                    resources_result = await session.list_resources()
                    print(f"   Found {len(resources_result.resources)} resources")
                except Exception as e:
                    print(f"   Resources not available: {e}")
                print()

                print("=" * 60)
                print("✓ All tests passed! Server is working correctly.")
                print("=" * 60)

    except httpx.ConnectError:
        print(f"✗ Error: Could not connect to {server_url}")
        print("  Make sure the server is running:")
        print("  python sse_server.py")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def test_tool_call(server_url: str = "http://localhost:8000/sse", tool_name: str = "list_models"):
    """Test calling a specific tool."""
    print(f"Testing tool call: {tool_name}")
    print("-" * 60)

    try:
        async with sse_client(server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                print(f"Calling tool: {tool_name}")
                result = await session.call_tool(tool_name, arguments={})

                print("Result:")
                print(json.dumps(result.model_dump(), indent=2))

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(description="Test ElevenLabs MCP SSE Server")
    parser.add_argument(
        "--url",
        default="http://localhost:8000/sse",
        help="SSE server URL (default: http://localhost:8000/sse)"
    )
    parser.add_argument(
        "--test-tool",
        help="Test a specific tool by name"
    )

    args = parser.parse_args()

    if args.test_tool:
        asyncio.run(test_tool_call(args.url, args.test_tool))
    else:
        asyncio.run(test_sse_connection(args.url))

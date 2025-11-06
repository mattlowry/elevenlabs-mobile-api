# ElevenLabs MCP SSE Server - Quick Start

Get your ElevenLabs MCP server running with SSE transport in under 5 minutes!

## Prerequisites

- Python 3.11+
- ElevenLabs API key ([get free key here](https://elevenlabs.io/app/settings/api-keys))

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Set Your API Key

```bash
export ELEVENLABS_API_KEY="your_api_key_here"
```

## 3. Start the Server

```bash
python sse_server.py
```

Or use the quick start script:

```bash
./quick_start_sse.sh
```

## 4. Test the Server

In another terminal:

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test SSE connection
python test_sse_client.py
```

## 5. Connect from Claude Desktop

Update your Claude Desktop configuration:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ElevenLabs-SSE": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

Restart Claude Desktop and you're ready!

## What's Next?

- **Deploy to cloud:** See [SSE_DEPLOYMENT_GUIDE.md](SSE_DEPLOYMENT_GUIDE.md)
- **Configure options:** Check available environment variables
- **Explore tools:** Ask Claude about available ElevenLabs capabilities

## Troubleshooting

**Server won't start?**
- Verify Python 3.11+: `python3 --version`
- Check API key is set: `echo $ELEVENLABS_API_KEY`
- Install dependencies: `pip install -r requirements.txt`

**Can't connect?**
- Ensure server is running on port 8000
- Check firewall settings
- Verify URL in Claude Desktop config

## Need Help?

- Full deployment guide: [SSE_DEPLOYMENT_GUIDE.md](SSE_DEPLOYMENT_GUIDE.md)
- Report issues: https://github.com/elevenlabs/elevenlabs-mcp/issues
- Community: https://discord.gg/elevenlabs

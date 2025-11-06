# ElevenLabs MCP SSE Server - Production Deployment Guide

This guide covers deploying the ElevenLabs MCP server with SSE (Server-Sent Events) transport for remote access from Claude Desktop and other MCP clients.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Local Development](#local-development)
- [Cloud Deployment](#cloud-deployment)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Security](#security)

## Overview

The SSE transport enables remote access to the ElevenLabs MCP server, allowing:
- Claude Desktop to connect to cloud-hosted servers
- Multiple clients to share a single server instance
- Deployment on cloud platforms (Render, Heroku, AWS, etc.)
- Serverless and containerized deployments

### Architecture

```
Claude Desktop → HTTP/SSE → Cloud Server → ElevenLabs API
                  (Internet)
```

## Quick Start

### Prerequisites

- Python 3.11 or higher
- ElevenLabs API key ([get one here](https://elevenlabs.io/app/settings/api-keys))
- Docker (for containerized deployment)

### Local Testing

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export ELEVENLABS_API_KEY="your_api_key_here"
   ```

3. **Run the server:**
   ```bash
   python sse_server.py
   ```

4. **Test the connection:**
   ```bash
   python test_sse_client.py
   ```

The server will be available at `http://localhost:8000/sse`

## Local Development

### Running with Docker

```bash
# Build the image
docker build -f Dockerfile.sse -t elevenlabs-mcp-sse .

# Run the container
docker run -p 8000:8000 \
  -e ELEVENLABS_API_KEY="your_key" \
  elevenlabs-mcp-sse
```

### Development Mode

For hot-reloading during development:

```bash
python sse_server.py
```

Access the server at:
- Health check: http://localhost:8000/health
- SSE endpoint: http://localhost:8000/sse
- API docs: http://localhost:8000/docs

## Cloud Deployment

### Render.com (Recommended)

1. **Fork/clone this repository**

2. **Connect to Render:**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Blueprint"
   - Connect your repository
   - Render will detect `render-sse-production.yaml`

3. **Configure environment variables:**
   - `ELEVENLABS_API_KEY`: Your ElevenLabs API key (required)
   - `ALLOWED_ORIGINS`: Comma-separated list of allowed origins
   - `ELEVENLABS_MCP_OUTPUT_MODE`: Set to `resources` for cloud deployment

4. **Deploy:**
   - Click "Apply"
   - Render will build and deploy automatically

5. **Get your endpoint:**
   - After deployment, note your Render URL: `https://your-app.onrender.com/sse`

### Other Platforms

#### Heroku

```bash
# Login to Heroku
heroku login

# Create app
heroku create elevenlabs-mcp-sse

# Set environment variables
heroku config:set ELEVENLABS_API_KEY="your_key"
heroku config:set ELEVENLABS_MCP_OUTPUT_MODE="resources"

# Deploy
git push heroku main
```

#### AWS ECS/Fargate

Use the provided `Dockerfile.sse` with AWS ECS:

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ECR_URL
docker build -f Dockerfile.sse -t elevenlabs-mcp-sse .
docker tag elevenlabs-mcp-sse:latest YOUR_ECR_URL/elevenlabs-mcp-sse:latest
docker push YOUR_ECR_URL/elevenlabs-mcp-sse:latest
```

#### Google Cloud Run

```bash
# Build and deploy
gcloud run deploy elevenlabs-mcp-sse \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ELEVENLABS_API_KEY="your_key"
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ELEVENLABS_API_KEY` | Yes | - | Your ElevenLabs API key |
| `HOST` | No | `0.0.0.0` | Server bind address |
| `PORT` | No | `8000` | Server port |
| `ELEVENLABS_MCP_OUTPUT_MODE` | No | `files` | Output mode: `files`, `resources`, or `both` |
| `ELEVENLABS_MCP_BASE_PATH` | No | `/tmp` | Base path for file operations |
| `ELEVENLABS_API_RESIDENCY` | No | `us` | Data residency: `us`, `eu-residency`, `in-residency`, `global` |
| `ALLOWED_ORIGINS` | No | `http://localhost` | Comma-separated allowed origins for CORS |

### Output Modes

- **`files`**: Save generated audio to disk (not recommended for cloud)
- **`resources`**: Return audio as base64-encoded resources (recommended for cloud)
- **`both`**: Both save to disk and return as resources

### Security Configuration

For production deployments, configure `ALLOWED_ORIGINS`:

```bash
export ALLOWED_ORIGINS="https://claude.ai,https://your-domain.com"
```

## Testing

### Test Server Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "server": "ElevenLabs MCP SSE",
  "transport": "sse",
  "mcp_version": "2025-03-26",
  "api_configured": true
}
```

### Test SSE Connection

```bash
python test_sse_client.py --url http://localhost:8000/sse
```

### Test Tool Execution

```bash
python test_sse_client.py --url http://localhost:8000/sse --test-tool list_models
```

## Connecting Claude Desktop

1. **Get your server URL** (e.g., `https://your-app.onrender.com/sse`)

2. **Update Claude Desktop config:**

   **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

   **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

   ```json
   {
     "mcpServers": {
       "ElevenLabs": {
         "url": "https://your-app.onrender.com/sse"
       }
     }
   }
   ```

3. **Restart Claude Desktop**

4. **Verify connection:**
   - Click the MCP icon in Claude Desktop
   - Check for "ElevenLabs" server
   - Should show "Connected" status

## Troubleshooting

### Server won't start

**Problem:** `ValueError: Missing required environment variables: ELEVENLABS_API_KEY`

**Solution:** Set the `ELEVENLABS_API_KEY` environment variable:
```bash
export ELEVENLABS_API_KEY="your_key_here"
```

### Can't connect from Claude Desktop

**Problem:** Connection timeout or refused

**Solution:**
1. Verify server is running: `curl https://your-server.com/health`
2. Check firewall/security group settings
3. Ensure `ALLOWED_ORIGINS` includes Claude Desktop origins
4. Check server logs for connection attempts

### Tools return errors

**Problem:** API calls fail with authentication errors

**Solution:**
1. Verify API key is valid: https://elevenlabs.io/app/settings/api-keys
2. Check API key has sufficient credits
3. Verify API key permissions

### High latency

**Problem:** Slow response times

**Solution:**
1. Deploy server closer to your region
2. Use faster ElevenLabs models (e.g., `eleven_flash_v2_5`)
3. Upgrade to paid Render plan for better performance

## Security

### Best Practices

1. **Never commit API keys:**
   - Use environment variables
   - Add `.env` to `.gitignore`

2. **Configure CORS:**
   ```bash
   export ALLOWED_ORIGINS="https://claude.ai,https://your-domain.com"
   ```

3. **Use HTTPS:**
   - Always deploy with HTTPS in production
   - Most cloud platforms provide this automatically

4. **Limit access:**
   - Use authentication/API keys for public deployments
   - Restrict by IP if possible

5. **Monitor usage:**
   - Track ElevenLabs API usage
   - Set up alerts for unusual activity
   - Use the `check_subscription` tool to monitor credits

## Advanced Topics

### Horizontal Scaling

To handle more concurrent users, deploy multiple instances:

**Render:**
- Increase `numInstances` in `render-sse-production.yaml`

**AWS/GCP:**
- Use auto-scaling groups or managed instance groups

### Custom Domains

Most cloud platforms support custom domains:

**Render:**
1. Go to Settings → Custom Domain
2. Add your domain
3. Update DNS records as instructed

### Monitoring

Set up monitoring for:
- Health endpoint: `/health`
- Response times
- Error rates
- ElevenLabs API usage

## Support

- **Issues:** https://github.com/elevenlabs/elevenlabs-mcp/issues
- **Documentation:** https://elevenlabs.io/docs
- **Community:** https://discord.gg/elevenlabs

## License

MIT License - see LICENSE file for details

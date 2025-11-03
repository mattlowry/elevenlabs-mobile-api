# Deployment Guide for ElevenLabs MCP Server

## Important Notes

**MCP (Model Context Protocol) servers communicate via stdio** and are designed to run locally as part of an MCP client integration (like Claude Desktop).

For **Render deployment**, this project includes a **web API wrapper** (`web_server.py`) that provides HTTP endpoints for health checks and basic functionality.

## Deployment Options

### 1. Local Installation (Recommended)

The standard way to use this MCP server:

```bash
# Install via uvx (recommended)
uvx elevenlabs-mcp

# Or install via pip
pip install elevenlabs-mcp
```

Then configure your MCP client (e.g., Claude Desktop) to use the server.

### 2. Docker Containerization

For isolated environments or testing:

```bash
# Build the Docker image
docker build -t elevenlabs-mcp .

# Run the container
docker run -e ELEVENLABS_API_KEY=your_key_here elevenlabs-mcp
```

### 3. Cloud Deployment Considerations

Since MCP servers use stdio communication, deploying to cloud platforms like Render requires special consideration:

#### Option A: Deploy as Part of a Larger Application
- Integrate the MCP server into a web application that acts as a bridge
- The web app communicates with the MCP server via stdio and exposes HTTP endpoints

#### Option B: Create an HTTP Wrapper
- Build a FastAPI/Flask wrapper around the MCP server
- Translate HTTP requests to MCP protocol messages
- Return MCP responses as HTTP responses

#### Option C: Use Render for CI/CD Only
- Use Render for building and testing
- Deploy to clients via package distribution (PyPI)

## Render Deployment (Web Service)

The included configuration deploys a web API wrapper that provides:
- Health check endpoint at `/health`
- API documentation at `/docs`
- Service information at `/api/info`

### Quick Deploy to Render

1. **Connect your repository to Render**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Blueprint"
   - Connect your Git repository
   - Render will automatically detect `render.yaml`

2. **Set the API key**
   - In Render dashboard, find the `ELEVENLABS_API_KEY` environment variable
   - Click "Generate Value" or manually enter your API key
   - **Never commit API keys to your repository**

3. **Deploy**
   - Render will build the Docker container and deploy
   - Health checks will verify the service is running
   - Access your service at the provided Render URL

### Manual Render Configuration

If not using `render.yaml`:

1. Create a new Web Service
2. Set runtime to "Docker"
3. Set Dockerfile path to `./Dockerfile`
4. Add environment variables (see below)
5. Set health check path to `/health`

**For production MCP client usage**, deploy to client machines directly using the package installation method.

## Environment Variables

Required:
- `ELEVENLABS_API_KEY`: Your ElevenLabs API key

Optional:
- `ELEVENLABS_MCP_BASE_PATH`: Base path for file operations (default: `~/Desktop`)
- `ELEVENLABS_MCP_OUTPUT_MODE`: Output mode - `files`, `resources`, or `both` (default: `files`)
- `ELEVENLABS_API_RESIDENCY`: Data residency region - `us`, `eu-residency`, `in-residency`, or `global` (default: `us`)

## Security Checklist

Before deployment:

- [ ] Remove all API keys from `.env` files
- [ ] Ensure `.env` is in `.gitignore`
- [ ] Use environment variables for sensitive data
- [ ] Review and update `render.yaml` environment variables
- [ ] Never commit API keys to version control

## Testing

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
./scripts/test.sh

# Test with MCP Inspector
mcp dev elevenlabs_mcp/server.py
```

## Support

For issues or questions:
- GitHub: https://github.com/elevenlabs/elevenlabs-mcp
- Documentation: See README.md

# Render Deployment Troubleshooting Guide

## Common Errors and Solutions

### Error: "No web process detected"
**Solution**: The project now includes `web_server.py` and updated Dockerfile. Make sure you're using the latest files.

### Error: "Health check failed"
**Cause**: Render couldn't reach the `/health` endpoint.

**Solutions**:
1. Verify Dockerfile is using `CMD ["python", "web_server.py"]`
2. Check that `PORT` environment variable is set to `8080`
3. Ensure `healthCheckPath` in render.yaml is set to `/health`

### Error: "Build failed" or "Docker build error"
**Solutions**:
1. Check that all files are committed to Git
2. Verify Dockerfile syntax
3. Check the build logs in Render dashboard for specific errors

### Error: "Environment variable not set"
**Solution**: In Render dashboard:
1. Go to your service
2. Click "Environment" tab
3. Add `ELEVENLABS_API_KEY` with your actual API key
4. Click "Save Changes"
5. Redeploy

### Error: "Service keeps restarting"
**Possible causes**:
1. **Missing API key**: Add `ELEVENLABS_API_KEY` environment variable
2. **Port mismatch**: Ensure PORT is set to 8080
3. **Dependency issues**: Check build logs for package installation errors

## Files Needed for Deployment

Make sure these files exist in your repository:

- ✅ `render.yaml` - Render configuration
- ✅ `Dockerfile` - Docker build instructions
- ✅ `web_server.py` - Web API wrapper
- ✅ `pyproject.toml` - Python dependencies
- ✅ `setup.py` - Package setup
- ✅ `.env.example` - Example environment variables (NOT .env)

## Verification Checklist

Before deploying:

- [ ] All files committed to Git
- [ ] No API keys in committed files
- [ ] `.env` is in `.gitignore` (it is by default)
- [ ] `render.yaml` exists in root directory
- [ ] `web_server.py` exists in root directory
- [ ] Dockerfile CMD is set to run web_server.py

## Testing Locally with Docker

Test your Docker setup before deploying:

```bash
# Build the image
docker build -t elevenlabs-mcp-test .

# Run with environment variable
docker run -p 8080:8080 \
  -e ELEVENLABS_API_KEY=your_key_here \
  elevenlabs-mcp-test

# Test the health endpoint
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "api_key_configured": true,
  "environment": {
    "base_path": "/tmp",
    "output_mode": "resources",
    "residency": "us"
  }
}
```

## Render Dashboard Navigation

1. **Logs**: Click on your service → "Logs" tab
2. **Environment Variables**: Service → "Environment" tab
3. **Deploy**: Service → "Manual Deploy" button
4. **Build Logs**: Available during deployment
5. **Runtime Logs**: Available after deployment

## Getting Help

If you're still having issues:

1. Check the **Logs** tab in Render dashboard
2. Copy the specific error message
3. Review the build logs for dependency issues
4. Verify all environment variables are set

## Important Notes

- **Web API vs MCP**: The deployed service is a web API wrapper, not a full MCP server
- **Health checks**: The `/health` endpoint verifies the service is running
- **API Documentation**: Available at `/docs` once deployed
- **Production use**: For MCP client integration, use local installation via pip/uvx

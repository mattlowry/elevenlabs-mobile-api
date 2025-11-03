# ElevenLabs Mobile API

🚀 **REST API for Mobile & Web Applications**

This project provides a production-ready REST API wrapper around ElevenLabs voice services, designed specifically for mobile and web applications.

## 🎯 What This Is

A **REST API server** that you can deploy to Render (or any cloud platform) that provides:

- ✅ Text-to-Speech API
- ✅ Voice Cloning API
- ✅ Speech-to-Text API
- ✅ Conversational AI Agents
- ✅ Sound Effects Generation
- ✅ Voice Management

## 🚀 Quick Deploy to Render

### 1. Prepare Your Repository

```bash
cd /Users/matthewlong/ElevenLabs-MCPv3/elevenlabs-mcp

# Make sure all files are committed
git add .
git commit -m "Add mobile API server"
git push origin main
```

### 2. Deploy to Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub repository
4. Render will auto-detect `render.yaml`
5. Click **"Apply"**

### 3. Set Environment Variables

In Render dashboard, set these environment variables:

- **`ELEVENLABS_API_KEY`**: Your ElevenLabs API key
- **`API_KEY`**: A secure random string (your custom API key)

Generate a secure API key:
```bash
openssl rand -hex 32
```

### 4. Test Your API

Once deployed, your API will be available at:
```
https://elevenlabsmcp.onrender.com
```

Test it:
```bash
# Health check
curl https://elevenlabsmcp.onrender.com/health

# API docs (interactive)
open https://elevenlabsmcp.onrender.com/docs
```

## 📱 Mobile App Integration

### Your API URL

After deployment, use this URL in your mobile app:

```
https://elevenlabsmcp.onrender.com
```

### Authentication

All API requests require this header:

```http
X-API-Key: your_custom_api_key
```

### Example: Text-to-Speech

```bash
curl -X POST https://elevenlabsmcp.onrender.com/api/tts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_custom_api_key" \
  -d '{
    "text": "Hello from my mobile app!",
    "voice_id": "cgSgspJ2msm6clMCkdW9"
  }'
```

**Response:**
```json
{
  "success": true,
  "audio": "base64_encoded_mp3_audio_data",
  "format": "mp3",
  "voice_id": "cgSgspJ2msm6clMCkdW9",
  "text_length": 25
}
```

## 📚 Complete API Documentation

See **[MOBILE_API.md](./MOBILE_API.md)** for:

- ✅ Complete endpoint reference
- ✅ Request/response examples
- ✅ iOS (Swift) integration code
- ✅ Android (Kotlin) integration code
- ✅ React Native integration code
- ✅ Flutter integration code
- ✅ Error handling
- ✅ Best practices

## 🔍 Interactive API Docs

Once deployed, visit:

```
https://elevenlabsmcp.onrender.com/docs
```

This provides:
- 📖 All endpoints with examples
- 🧪 "Try it out" testing interface
- 📋 Request/response schemas
- 🔐 Authentication testing

## 🛠️ Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (no auth) |
| `/api/tts` | POST | Text to speech |
| `/api/tts/stream` | POST | Stream audio (for long texts) |
| `/api/voices` | GET | List all voices |
| `/api/voices/{id}` | GET | Get voice details |
| `/api/voices/clone` | POST | Clone a voice |
| `/api/agents` | GET | List AI agents |
| `/api/agents` | POST | Create AI agent |
| `/api/agents/{id}` | GET | Get agent details |
| `/api/sfx` | POST | Generate sound effects |
| `/api/stt` | POST | Speech to text |

## 🔐 Security Setup

### Generate Secure API Key

```bash
# Generate a 32-byte random hex string
openssl rand -hex 32
```

Use this as your `API_KEY` environment variable in Render.

### In Your Mobile App

**❌ DON'T:** Hardcode API keys in your app source code

**✅ DO:** Store API keys securely:

**iOS (Swift):**
```swift
// Store in Keychain
let keychain = KeychainSwift()
keychain.set("your_api_key", forKey: "elevenlabs_api_key")
```

**Android (Kotlin):**
```kotlin
// Use EncryptedSharedPreferences
val preferences = EncryptedSharedPreferences.create(...)
preferences.edit().putString("api_key", "your_api_key").apply()
```

**React Native:**
```javascript
// Use react-native-keychain
import * as Keychain from 'react-native-keychain';
await Keychain.setGenericPassword('api_key', 'your_api_key');
```

## 📊 Monitor Your API

### Render Dashboard

- **Logs**: See real-time request logs
- **Metrics**: Monitor CPU, memory, response times
- **Events**: Track deployments and errors

### ElevenLabs Dashboard

Monitor your ElevenLabs usage:
https://elevenlabs.io/app/usage

## 💰 Costs

### Render Hosting
- **Starter Plan**: $7/month
- Includes: 512MB RAM, 0.5 CPU
- Auto-sleep after inactivity (configurable)

### ElevenLabs API
- **Free Tier**: 10,000 characters/month
- **Paid Plans**: Starting at $5/month
- See: https://elevenlabs.io/pricing

## 🐛 Troubleshooting

### API Returns 401 Unauthorized

**Problem**: Missing or invalid API key

**Solution**:
1. Check `X-API-Key` header in your request
2. Verify API_KEY environment variable in Render

### API Returns 500 Error

**Problem**: ElevenLabs API key issue

**Solution**:
1. Check Render logs for detailed error
2. Verify ELEVENLABS_API_KEY is set correctly
3. Test ElevenLabs key at https://elevenlabs.io

### Health Check Fails

**Problem**: Server not responding

**Solution**:
1. Check Render deployment logs
2. Verify Dockerfile is correct
3. Ensure port 8080 is exposed

### CORS Errors (Web Apps)

**Problem**: Browser blocks API requests

**Solution**: Update CORS settings in `api_server.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📖 Additional Documentation

- **[MOBILE_API.md](./MOBILE_API.md)** - Complete API reference with code examples
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Deployment guide and options
- **[RENDER_TROUBLESHOOTING.md](./RENDER_TROUBLESHOOTING.md)** - Common issues and solutions

## 🎓 Example Projects

### iOS Example (Swift)
See `MOBILE_API.md` for complete iOS integration with AVAudioPlayer

### Android Example (Kotlin)
See `MOBILE_API.md` for complete Android integration with MediaPlayer

### React Native Example
See `MOBILE_API.md` for complete React Native integration

### Flutter Example
See `MOBILE_API.md` for complete Flutter integration

## 🚀 Next Steps

1. ✅ Deploy to Render
2. ✅ Test with `/docs` interface
3. ✅ Integrate into your mobile app
4. ✅ Monitor usage and optimize
5. ✅ Scale as needed

**Your mobile API is ready!** 🎉

## 📞 Support

- **GitHub Issues**: Report bugs and feature requests
- **ElevenLabs Docs**: https://elevenlabs.io/docs
- **Render Docs**: https://render.com/docs

---

**Made with ❤️ for mobile developers**

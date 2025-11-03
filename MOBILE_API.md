# ElevenLabs Mobile API Documentation

## Overview

This REST API provides ElevenLabs voice services for mobile and web applications. Deploy to Render and access from any platform that supports HTTP requests.

**Base URL**: `https://your-app.onrender.com`
**API Documentation**: `https://your-app.onrender.com/docs`

## Authentication

All API endpoints (except `/health`) require authentication via API key header:

```http
X-API-Key: your_api_key_here
```

## Quick Start

### 1. Deploy to Render

1. Push your code to GitHub
2. Connect to Render
3. Set environment variables:
   - `ELEVENLABS_API_KEY`: Your ElevenLabs API key
   - `API_KEY`: Custom API key for your mobile app clients

### 2. Test the API

```bash
# Health check (no auth required)
curl https://your-app.onrender.com/health

# Test text-to-speech
curl -X POST https://your-app.onrender.com/api/tts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"text": "Hello world!"}'
```

## API Endpoints

### 🏥 Health & Status

#### GET `/health`
Check API status (no auth required)

**Response:**
```json
{
  "status": "healthy",
  "api_configured": true,
  "endpoints": {
    "text_to_speech": "/api/tts",
    "voices": "/api/voices",
    "voice_clone": "/api/voices/clone",
    "agents": "/api/agents",
    "sound_effects": "/api/sfx"
  }
}
```

---

### 🎙️ Text-to-Speech

#### POST `/api/tts`
Convert text to speech

**Request Body:**
```json
{
  "text": "Hello, this is a test",
  "voice_id": "optional_voice_id",
  "model_id": "eleven_multilingual_v2",
  "stability": 0.5,
  "similarity_boost": 0.75,
  "style": 0,
  "use_speaker_boost": true
}
```

**Response:**
```json
{
  "success": true,
  "audio": "base64_encoded_audio_data",
  "format": "mp3",
  "voice_id": "cgSgspJ2msm6clMCkdW9",
  "text_length": 22
}
```

**Mobile Usage (Swift):**
```swift
// Decode base64 audio
if let audioData = Data(base64Encoded: response.audio) {
    let audioPlayer = try AVAudioPlayer(data: audioData)
    audioPlayer.play()
}
```

**Mobile Usage (React Native):**
```javascript
// Play base64 audio
import Sound from 'react-native-sound';

const sound = new Sound('data:audio/mp3;base64,' + response.audio, '', (error) => {
  if (!error) {
    sound.play();
  }
});
```

#### POST `/api/tts/stream`
Stream audio for longer texts (same request body)

Returns audio stream directly instead of base64.

---

### 🎤 Voice Management

#### GET `/api/voices`
List all available voices

**Response:**
```json
{
  "success": true,
  "count": 50,
  "voices": [
    {
      "voice_id": "21m00Tcm4TlvDq8ikWAM",
      "name": "Rachel",
      "category": "premade",
      "description": "Calm American female voice",
      "labels": {"accent": "american", "age": "young"}
    }
  ]
}
```

#### GET `/api/voices/{voice_id}`
Get details of a specific voice

**Response:**
```json
{
  "success": true,
  "voice": {
    "voice_id": "21m00Tcm4TlvDq8ikWAM",
    "name": "Rachel",
    "category": "premade",
    "description": "Calm American female voice",
    "labels": {"accent": "american", "age": "young"},
    "samples": []
  }
}
```

#### POST `/api/voices/clone`
Clone a voice from audio samples

**Request:**
- Content-Type: `multipart/form-data`
- Files: 1-25 audio files (MP3, WAV, M4A)
- Body fields:
  - `name`: Voice name
  - `description`: Optional description

**Response:**
```json
{
  "success": true,
  "voice_id": "new_voice_id",
  "name": "My Cloned Voice",
  "message": "Voice cloned successfully"
}
```

---

### 🤖 Conversational AI Agents

#### GET `/api/agents`
List all conversational AI agents

**Response:**
```json
{
  "success": true,
  "count": 3,
  "agents": [
    {
      "agent_id": "agent123",
      "name": "Customer Support Bot",
      "conversation_config": {}
    }
  ]
}
```

#### POST `/api/agents`
Create a new conversational AI agent

**Request Body:**
```json
{
  "name": "My Agent",
  "first_message": "Hello! How can I help you?",
  "system_prompt": "You are a helpful assistant...",
  "voice_id": "optional_voice_id",
  "language": "en",
  "temperature": 0.7
}
```

**Response:**
```json
{
  "success": true,
  "agent_id": "new_agent_id",
  "name": "My Agent",
  "message": "Agent created successfully"
}
```

#### GET `/api/agents/{agent_id}`
Get details of a specific agent

---

### 🔊 Sound Effects

#### POST `/api/sfx`
Generate sound effects from text description

**Request Body:**
```json
{
  "text": "Thunder and rain in a forest",
  "duration_seconds": 3.5
}
```

**Response:**
```json
{
  "success": true,
  "audio": "base64_encoded_audio_data",
  "format": "mp3",
  "duration": 3.5,
  "description": "Thunder and rain in a forest"
}
```

---

### 📝 Speech-to-Text

#### POST `/api/stt`
Transcribe speech from audio file

**Request:**
- Content-Type: `multipart/form-data`
- File: Audio file to transcribe
- Query params:
  - `language`: Optional language code (e.g., "en", "es")
  - `diarize`: Boolean for speaker identification

**Response:**
```json
{
  "success": true,
  "transcript": "This is the transcribed text",
  "language": "en",
  "diarization": false
}
```

---

## Mobile App Integration Examples

### iOS (Swift)

```swift
import Foundation

class ElevenLabsAPI {
    let baseURL = "https://your-app.onrender.com"
    let apiKey = "your_api_key"

    func textToSpeech(text: String, completion: @escaping (Data?) -> Void) {
        let url = URL(string: "\(baseURL)/api/tts")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")

        let body: [String: Any] = ["text": text]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        URLSession.shared.dataTask(with: request) { data, response, error in
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let audioBase64 = json["audio"] as? String,
                  let audioData = Data(base64Encoded: audioBase64) else {
                completion(nil)
                return
            }
            completion(audioData)
        }.resume()
    }
}
```

### Android (Kotlin)

```kotlin
import okhttp3.*
import org.json.JSONObject
import android.util.Base64

class ElevenLabsAPI {
    private val client = OkHttpClient()
    private val baseUrl = "https://your-app.onrender.com"
    private val apiKey = "your_api_key"

    fun textToSpeech(text: String, callback: (ByteArray?) -> Unit) {
        val json = JSONObject().apply {
            put("text", text)
        }

        val request = Request.Builder()
            .url("$baseUrl/api/tts")
            .addHeader("Content-Type", "application/json")
            .addHeader("X-API-Key", apiKey)
            .post(RequestBody.create(
                MediaType.parse("application/json"),
                json.toString()
            ))
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                val responseData = response.body()?.string()
                val jsonResponse = JSONObject(responseData)
                val audioBase64 = jsonResponse.getString("audio")
                val audioBytes = Base64.decode(audioBase64, Base64.DEFAULT)
                callback(audioBytes)
            }

            override fun onFailure(call: Call, e: IOException) {
                callback(null)
            }
        })
    }
}
```

### React Native

```javascript
import axios from 'axios';

const ELEVENLABS_API = {
  baseURL: 'https://your-app.onrender.com',
  apiKey: 'your_api_key',
};

export async function textToSpeech(text) {
  try {
    const response = await axios.post(
      `${ELEVENLABS_API.baseURL}/api/tts`,
      { text },
      {
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': ELEVENLABS_API.apiKey,
        },
      }
    );

    return response.data.audio; // base64 encoded
  } catch (error) {
    console.error('TTS Error:', error);
    return null;
  }
}

// Usage
import Sound from 'react-native-sound';

const audioBase64 = await textToSpeech('Hello world!');
const sound = new Sound(`data:audio/mp3;base64,${audioBase64}`, '', (error) => {
  if (!error) {
    sound.play();
  }
});
```

### Flutter

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:audioplayers/audioplayers.dart';

class ElevenLabsAPI {
  static const String baseUrl = 'https://your-app.onrender.com';
  static const String apiKey = 'your_api_key';

  static Future<void> textToSpeech(String text) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/tts'),
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
      body: jsonEncode({'text': text}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      final audioBase64 = data['audio'];
      final audioBytes = base64Decode(audioBase64);

      // Play audio
      final player = AudioPlayer();
      await player.play(BytesSource(audioBytes));
    }
  }
}
```

---

## Error Handling

All endpoints return standard HTTP status codes:

- `200`: Success
- `400`: Bad request (invalid parameters)
- `401`: Unauthorized (missing or invalid API key)
- `404`: Resource not found
- `500`: Server error

**Error Response Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Rate Limiting

The API inherits rate limits from your ElevenLabs account:
- Free tier: 10,000 characters/month
- Paid tiers: See ElevenLabs pricing

Consider implementing client-side caching and rate limiting in your mobile app.

---

## Security Best Practices

1. **Never commit API keys** to your mobile app source code
2. **Use environment variables** or secure config management
3. **Implement API key rotation** for production apps
4. **Restrict CORS origins** in production (update `api_server.py`)
5. **Add request signing** for additional security
6. **Monitor API usage** in Render dashboard

---

## Testing

Use the interactive API documentation at `/docs` to test endpoints:

```
https://your-app.onrender.com/docs
```

This provides a Swagger UI with all endpoints, request/response schemas, and a "Try it out" feature.

---

## Support

- **API Issues**: Check `/health` endpoint and Render logs
- **ElevenLabs API**: https://elevenlabs.io/docs
- **Render Support**: https://render.com/docs

---

## Next Steps

1. ✅ Deploy to Render
2. ✅ Set API keys in environment variables
3. ✅ Test endpoints with `/docs` interface
4. ✅ Integrate into your mobile app
5. ✅ Monitor usage and costs

**Your API is ready to use!** 🚀

"""
ElevenLabs REST API Server for Mobile Apps
Deploy this to Render to create an API that mobile apps can consume
"""

from fastapi import FastAPI, HTTPException, Header, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
import uvicorn
import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import base64
from io import BytesIO

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="ElevenLabs Mobile API",
    description="REST API for ElevenLabs voice services - designed for mobile apps",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for mobile/web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ElevenLabs client
client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# ============================================================================
# Authentication
# ============================================================================

async def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key from request header"""
    expected_key = os.getenv("API_KEY")
    if expected_key and x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# ============================================================================
# Request/Response Models
# ============================================================================

class TextToSpeechRequest(BaseModel):
    text: str = Field(..., description="Text to convert to speech")
    voice_id: Optional[str] = Field(None, description="Voice ID to use")
    model_id: str = Field("eleven_multilingual_v2", description="Model ID")
    stability: float = Field(0.5, ge=0, le=1)
    similarity_boost: float = Field(0.75, ge=0, le=1)
    style: float = Field(0, ge=0, le=1)
    use_speaker_boost: bool = True


class VoiceCloneRequest(BaseModel):
    name: str = Field(..., description="Name for the cloned voice")
    description: Optional[str] = Field(None, description="Voice description")


class AgentCreateRequest(BaseModel):
    name: str
    first_message: str
    system_prompt: str
    voice_id: Optional[str] = None
    language: str = "en"
    temperature: float = Field(0.5, ge=0, le=1)


class SoundEffectRequest(BaseModel):
    text: str = Field(..., description="Description of the sound effect")
    duration_seconds: float = Field(2.0, ge=0.5, le=5.0)


# ============================================================================
# Health & Info Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ElevenLabs Mobile API",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    api_key_configured = bool(os.getenv("ELEVENLABS_API_KEY"))

    return {
        "status": "healthy",
        "api_configured": api_key_configured,
        "endpoints": {
            "text_to_speech": "/api/tts",
            "voices": "/api/voices",
            "voice_clone": "/api/voices/clone",
            "agents": "/api/agents",
            "sound_effects": "/api/sfx"
        }
    }


# ============================================================================
# Text-to-Speech Endpoints
# ============================================================================

@app.post("/api/tts", dependencies=[Depends(verify_api_key)])
async def text_to_speech(request: TextToSpeechRequest):
    """
    Convert text to speech

    Returns base64 encoded audio that can be decoded in mobile app
    """
    try:
        # Use default voice if none specified
        voice_id = request.voice_id or os.getenv("ELEVENLABS_DEFAULT_VOICE_ID", "cgSgspJ2msm6clMCkdW9")

        # Generate speech
        audio_generator = client.text_to_speech.convert(
            voice_id=voice_id,
            text=request.text,
            model_id=request.model_id,
            voice_settings={
                "stability": request.stability,
                "similarity_boost": request.similarity_boost,
                "style": request.style,
                "use_speaker_boost": request.use_speaker_boost,
            }
        )

        # Collect audio bytes
        audio_bytes = b"".join(audio_generator)

        # Encode to base64 for mobile transmission
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        return {
            "success": True,
            "audio": audio_base64,
            "format": "mp3",
            "voice_id": voice_id,
            "text_length": len(request.text)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")


@app.post("/api/tts/stream", dependencies=[Depends(verify_api_key)])
async def text_to_speech_stream(request: TextToSpeechRequest):
    """
    Stream audio response (for larger texts)
    """
    try:
        voice_id = request.voice_id or os.getenv("ELEVENLABS_DEFAULT_VOICE_ID", "cgSgspJ2msm6clMCkdW9")

        audio_generator = client.text_to_speech.convert(
            voice_id=voice_id,
            text=request.text,
            model_id=request.model_id,
            voice_settings={
                "stability": request.stability,
                "similarity_boost": request.similarity_boost,
            }
        )

        return StreamingResponse(
            audio_generator,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS streaming failed: {str(e)}")


# ============================================================================
# Voice Management Endpoints
# ============================================================================

@app.get("/api/voices", dependencies=[Depends(verify_api_key)])
async def list_voices():
    """List all available voices"""
    try:
        voices = client.voices.get_all()

        voice_list = [
            {
                "voice_id": voice.voice_id,
                "name": voice.name,
                "category": voice.category,
                "description": getattr(voice, 'description', ''),
                "labels": getattr(voice, 'labels', {}),
            }
            for voice in voices.voices
        ]

        return {
            "success": True,
            "count": len(voice_list),
            "voices": voice_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list voices: {str(e)}")


@app.get("/api/voices/{voice_id}", dependencies=[Depends(verify_api_key)])
async def get_voice(voice_id: str):
    """Get details of a specific voice"""
    try:
        voice = client.voices.get(voice_id)

        return {
            "success": True,
            "voice": {
                "voice_id": voice.voice_id,
                "name": voice.name,
                "category": voice.category,
                "description": getattr(voice, 'description', ''),
                "labels": getattr(voice, 'labels', {}),
                "samples": getattr(voice, 'samples', [])
            }
        }

    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Voice not found: {str(e)}")


@app.post("/api/voices/clone", dependencies=[Depends(verify_api_key)])
async def clone_voice(
    request: VoiceCloneRequest,
    files: List[UploadFile] = File(...)
):
    """
    Clone a voice from audio samples

    Upload 1-25 audio files (MP3, WAV, M4A)
    """
    try:
        # Read uploaded files
        audio_files = []
        for file in files:
            audio_bytes = await file.read()
            audio_files.append((file.filename, audio_bytes))

        # Clone the voice
        voice = client.clone(
            name=request.name,
            description=request.description or f"Cloned voice: {request.name}",
            files=audio_files
        )

        return {
            "success": True,
            "voice_id": voice.voice_id,
            "name": voice.name,
            "message": "Voice cloned successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice cloning failed: {str(e)}")


# ============================================================================
# Conversational AI Endpoints
# ============================================================================

@app.get("/api/agents", dependencies=[Depends(verify_api_key)])
async def list_agents():
    """List all conversational AI agents"""
    try:
        agents = client.conversational_ai.get_agents()

        agent_list = [
            {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "conversation_config": agent.conversation_config
            }
            for agent in agents
        ]

        return {
            "success": True,
            "count": len(agent_list),
            "agents": agent_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")


@app.post("/api/agents", dependencies=[Depends(verify_api_key)])
async def create_agent(request: AgentCreateRequest):
    """Create a new conversational AI agent"""
    try:
        from elevenlabs_mcp.convai import create_conversation_config

        conversation_config = create_conversation_config(
            agent_name=request.name,
            first_message=request.first_message,
            system_prompt=request.system_prompt,
            language=request.language,
            temperature=request.temperature,
        )

        agent = client.conversational_ai.create_agent(
            conversation_config=conversation_config
        )

        return {
            "success": True,
            "agent_id": agent.agent_id,
            "name": request.name,
            "message": "Agent created successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent creation failed: {str(e)}")


@app.get("/api/agents/{agent_id}", dependencies=[Depends(verify_api_key)])
async def get_agent(agent_id: str):
    """Get details of a specific agent"""
    try:
        agent = client.conversational_ai.get_agent(agent_id)

        return {
            "success": True,
            "agent": {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "config": agent.conversation_config
            }
        }

    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Agent not found: {str(e)}")


# ============================================================================
# Sound Effects Endpoints
# ============================================================================

@app.post("/api/sfx", dependencies=[Depends(verify_api_key)])
async def generate_sound_effect(request: SoundEffectRequest):
    """Generate a sound effect from text description"""
    try:
        audio = client.text_to_sound_effects.convert(
            text=request.text,
            duration_seconds=request.duration_seconds,
        )

        # Collect audio bytes
        audio_bytes = b"".join(audio)

        # Encode to base64
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        return {
            "success": True,
            "audio": audio_base64,
            "format": "mp3",
            "duration": request.duration_seconds,
            "description": request.text
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sound effect generation failed: {str(e)}")


# ============================================================================
# Speech to Text Endpoints
# ============================================================================

@app.post("/api/stt", dependencies=[Depends(verify_api_key)])
async def speech_to_text(
    file: UploadFile = File(...),
    language: Optional[str] = None,
    diarize: bool = False
):
    """
    Convert speech to text

    Upload an audio file to transcribe
    """
    try:
        audio_bytes = await file.read()

        # Create file-like object
        audio_file = BytesIO(audio_bytes)
        audio_file.name = file.filename

        # Transcribe
        result = client.speech_to_text.convert(
            audio=audio_file,
            language=language,
            diarize=diarize
        )

        return {
            "success": True,
            "transcript": result.text if hasattr(result, 'text') else str(result),
            "language": language or "auto-detected",
            "diarization": diarize
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech-to-text failed: {str(e)}")


# ============================================================================
# Server Startup
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

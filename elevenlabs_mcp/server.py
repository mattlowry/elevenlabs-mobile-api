"""
ElevenLabs MCP Server

⚠️ IMPORTANT: This server provides access to ElevenLabs API endpoints which may incur costs.
Each tool that makes an API call is marked with a cost warning. Please follow these guidelines:

1. Only use tools when explicitly requested by the user
2. For tools that generate audio, consider the length of the text as it affects costs
3. Some operations like voice cloning or text-to-voice may have higher costs

Tools without cost warnings in their description are free to use as they only read existing data.
"""

import httpx
import os
import base64
from datetime import datetime
from io import BytesIO
from typing import Literal, Union
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import (
    TextContent,
    Resource,
    EmbeddedResource,
)
from elevenlabs.client import ElevenLabs
from elevenlabs.types import MusicPrompt
from elevenlabs_mcp.model import McpVoice, McpModel, McpLanguage
from elevenlabs_mcp.utils import (
    make_error,
    make_output_path,
    make_output_file,
    handle_input_file,
    parse_conversation_transcript,
    handle_large_text,
    parse_location,
    get_mime_type,
    handle_output_mode,
    handle_multiple_files_output_mode,
    get_output_mode_description,
)

from elevenlabs_mcp.convai import create_conversation_config, create_platform_settings
from elevenlabs.types.knowledge_base_locator import KnowledgeBaseLocator

from elevenlabs.play import play
from elevenlabs_mcp import __version__
from pathlib import Path

load_dotenv()
api_key = os.getenv("ELEVENLABS_API_KEY")
base_path = os.getenv("ELEVENLABS_MCP_BASE_PATH")
output_mode = os.getenv("ELEVENLABS_MCP_OUTPUT_MODE", "files").strip().lower()
DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_DEFAULT_VOICE_ID", "cgSgspJ2msm6clMCkdW9")

if output_mode not in {"files", "resources", "both"}:
    raise ValueError("ELEVENLABS_MCP_OUTPUT_MODE must be one of: 'files', 'resources', 'both'")
if not api_key:
    raise ValueError("ELEVENLABS_API_KEY environment variable is required")

origin = parse_location(os.getenv("ELEVENLABS_API_RESIDENCY"))

# Add custom client to ElevenLabs to set User-Agent header
custom_client = httpx.Client(
    headers={
        "User-Agent": f"ElevenLabs-MCP/{__version__}",
    },
)

client = ElevenLabs(api_key=api_key, httpx_client=custom_client, base_url=origin)
mcp = FastMCP("ElevenLabs")


def format_diarized_transcript(transcription) -> str:
    """Format transcript with speaker labels from diarized response."""
    try:
        # Try to access words array - the exact attribute might vary
        words = None
        if hasattr(transcription, "words"):
            words = transcription.words
        elif hasattr(transcription, "__dict__"):
            # Try to find words in the response dict
            for key, value in transcription.__dict__.items():
                if key == "words" or (
                    isinstance(value, list)
                    and len(value) > 0
                    and (
                        hasattr(value[0], "speaker_id")
                        if hasattr(value[0], "__dict__")
                        else (
                            "speaker_id" in value[0]
                            if isinstance(value[0], dict)
                            else False
                        )
                    )
                ):
                    words = value
                    break

        if not words:
            return transcription.text

        formatted_lines = []
        current_speaker = None
        current_text = []

        for word in words:
            # Get speaker_id - might be an attribute or dict key
            word_speaker = None
            if hasattr(word, "speaker_id"):
                word_speaker = word.speaker_id
            elif isinstance(word, dict) and "speaker_id" in word:
                word_speaker = word["speaker_id"]

            # Get text - might be an attribute or dict key
            word_text = None
            if hasattr(word, "text"):
                word_text = word.text
            elif isinstance(word, dict) and "text" in word:
                word_text = word["text"]

            if not word_speaker or not word_text:
                continue

            # Skip spacing/punctuation types if they exist
            if hasattr(word, "type") and word.type == "spacing":
                continue
            elif isinstance(word, dict) and word.get("type") == "spacing":
                continue

            if current_speaker != word_speaker:
                # Save previous speaker's text
                if current_speaker and current_text:
                    speaker_label = current_speaker.upper().replace("_", " ")
                    formatted_lines.append(f"{speaker_label}: {' '.join(current_text)}")

                # Start new speaker
                current_speaker = word_speaker
                current_text = [word_text.strip()]
            else:
                current_text.append(word_text.strip())

        # Add final speaker's text
        if current_speaker and current_text:
            speaker_label = current_speaker.upper().replace("_", " ")
            formatted_lines.append(f"{speaker_label}: {' '.join(current_text)}")

        return "\n\n".join(formatted_lines)

    except Exception:
        # Fallback to regular text if something goes wrong
        return transcription.text
@mcp.resource("elevenlabs://{filename}")
def get_elevenlabs_resource(filename: str) -> Resource:
    """
    Resource handler for ElevenLabs generated files.
    """
    candidate = Path(filename)
    base_dir = make_output_path(None, base_path)

    if candidate.is_absolute():
        file_path = candidate.resolve()
    else:
        base_dir_resolved = base_dir.resolve()
        resolved_file = (base_dir_resolved / candidate).resolve()
        try:
            resolved_file.relative_to(base_dir_resolved)
        except ValueError:
            make_error(
                f"Resource path ({resolved_file}) is outside of allowed directory {base_dir_resolved}"
            )
        file_path = resolved_file

    if not file_path.exists():
        raise FileNotFoundError(f"Resource file not found: {filename}")

    # Read the file and determine MIME type
    try:
        with open(file_path, "rb") as f:
            file_data = f.read()
    except IOError as e:
        raise FileNotFoundError(f"Failed to read resource file {filename}: {e}")

    file_extension = file_path.suffix.lstrip(".")
    mime_type = get_mime_type(file_extension)

    # For text files, return text content
    if mime_type.startswith("text/"):
        try:
            text_content = file_data.decode("utf-8")
            return Resource(
                uri=f"elevenlabs://{filename}", mimeType=mime_type, text=text_content
            )
        except UnicodeDecodeError:
            make_error(
                f"Failed to decode text resource {filename} as UTF-8; MIME type {mime_type} may be incorrect or file is corrupt"
            )

    # For binary files, return base64 encoded data
    base64_data = base64.b64encode(file_data).decode("utf-8")
    return Resource(
        uri=f"elevenlabs://{filename}", mimeType=mime_type, data=base64_data
    )


@mcp.tool(
    description=f"""Convert text to speech with a given voice. {get_output_mode_description(output_mode)}.
    
    Only one of voice_id or voice_name can be provided. If none are provided, the default voice will be used.

    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs. Only use when explicitly requested by the user.

     Args:
        text (str): The text to convert to speech.
        voice_name (str, optional): The name of the voice to use.
        model_id (str, optional): The model ID to use for speech synthesis. Options include:
            - eleven_multilingual_v2: High quality multilingual model (29 languages)
            - eleven_flash_v2_5: Fastest model with ultra-low latency (32 languages)
            - eleven_turbo_v2_5: Balanced quality and speed (32 languages)
            - eleven_flash_v2: Fast English-only model
            - eleven_turbo_v2: Balanced English-only model
            - eleven_monolingual_v1: Legacy English model
            Defaults to eleven_multilingual_v2 or environment variable ELEVENLABS_MODEL_ID.
        stability (float, optional): Stability of the generated audio. Determines how stable the voice is and the randomness between each generation. Lower values introduce broader emotional range for the voice. Higher values can result in a monotonous voice with limited emotion. Range is 0 to 1.
        similarity_boost (float, optional): Similarity boost of the generated audio. Determines how closely the AI should adhere to the original voice when attempting to replicate it. Range is 0 to 1.
        style (float, optional): Style of the generated audio. Determines the style exaggeration of the voice. This setting attempts to amplify the style of the original speaker. It does consume additional computational resources and might increase latency if set to anything other than 0. Range is 0 to 1.
        use_speaker_boost (bool, optional): Use speaker boost of the generated audio. This setting boosts the similarity to the original speaker. Using this setting requires a slightly higher computational load, which in turn increases latency.
        speed (float, optional): Speed of the generated audio. Controls the speed of the generated speech. Values range from 0.7 to 1.2, with 1.0 being the default speed. Lower values create slower, more deliberate speech while higher values produce faster-paced speech. Extreme values can impact the quality of the generated speech. Range is 0.7 to 1.2.
        output_directory (str, optional): Directory where files should be saved (only used when saving files).
            Defaults to $HOME/Desktop if not provided.
        language: ISO 639-1 language code for the voice.
        output_format (str, optional): Output format of the generated audio. Formatted as codec_sample_rate_bitrate. So an mp3 with 22.05kHz sample rate at 32kbs is represented as mp3_22050_32. MP3 with 192kbps bitrate requires you to be subscribed to Creator tier or above. PCM with 44.1kHz sample rate requires you to be subscribed to Pro tier or above. Note that the μ-law format (sometimes written mu-law, often approximated as u-law) is commonly used for Twilio audio inputs.
            Defaults to "mp3_44100_128". Must be one of:
            mp3_22050_32
            mp3_44100_32
            mp3_44100_64
            mp3_44100_96
            mp3_44100_128
            mp3_44100_192
            pcm_8000
            pcm_16000
            pcm_22050
            pcm_24000
            pcm_44100
            ulaw_8000
            alaw_8000
            opus_48000_32
            opus_48000_64
            opus_48000_96
            opus_48000_128
            opus_48000_192

    Returns:
        Text content with file path or MCP resource with audio data, depending on output mode.
    """
)
def text_to_speech(
    text: str,
    voice_name: str | None = None,
    output_directory: str | None = None,
    voice_id: str | None = None,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0,
    use_speaker_boost: bool = True,
    speed: float = 1.0,
    language: str = "en",
    output_format: str = "mp3_44100_128",
    model_id: str | None = None,
) -> Union[TextContent, EmbeddedResource]:
    if text == "":
        make_error("Text is required.")

    if voice_id is not None and voice_name is not None:
        make_error("voice_id and voice_name cannot both be provided.")

    voice = None
    if voice_id is not None:
        voice = client.voices.get(voice_id=voice_id)
    elif voice_name is not None:
        voices = client.voices.search(search=voice_name)
        if len(voices.voices) == 0:
            make_error("No voices found with that name.")
        voice = next((v for v in voices.voices if v.name == voice_name), None)
        if voice is None:
            make_error(f"Voice with name: {voice_name} does not exist.")

    voice_id = voice.voice_id if voice else DEFAULT_VOICE_ID

    output_path = make_output_path(output_directory, base_path)
    output_file_name = make_output_file("tts", text, "mp3")

    if model_id is None:
        model_id = (
            "eleven_flash_v2_5"
            if language in ["hu", "no", "vi"]
            else "eleven_multilingual_v2"
        )

    audio_data = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format=output_format,
        voice_settings={
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": use_speaker_boost,
            "speed": speed,
        },
    )
    audio_bytes = b"".join(audio_data)

    # Handle different output modes
    success_message = f"Success. File saved as: {{file_path}}. Voice used: {voice.name if voice else DEFAULT_VOICE_ID}"
    return handle_output_mode(
        audio_bytes, output_path, output_file_name, output_mode, success_message
    )


@mcp.tool(
    description=f"""Transcribe speech from an audio file. When save_transcript_to_file=True: {get_output_mode_description(output_mode)}. When return_transcript_to_client_directly=True, always returns text directly regardless of output mode.

    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs. Only use when explicitly requested by the user.

    Args:
        file_path: Path to the audio file to transcribe
        language_code: ISO 639-3 language code for transcription. If not provided, the language will be detected automatically.
        diarize: Whether to diarize the audio file. If True, which speaker is currently speaking will be annotated in the transcription.
        save_transcript_to_file: Whether to save the transcript to a file.
        return_transcript_to_client_directly: Whether to return the transcript to the client directly.
        output_directory: Directory where files should be saved (only used when saving files).
            Defaults to $HOME/Desktop if not provided.

    Returns:
        TextContent containing the transcription or MCP resource with transcript data.
    """
)
def speech_to_text(
    input_file_path: str,
    language_code: str | None = None,
    diarize: bool = False,
    save_transcript_to_file: bool = True,
    return_transcript_to_client_directly: bool = False,
    output_directory: str | None = None,
) -> Union[TextContent, EmbeddedResource]:
    if not save_transcript_to_file and not return_transcript_to_client_directly:
        make_error("Must save transcript to file or return it to the client directly.")
    file_path = handle_input_file(input_file_path)
    if save_transcript_to_file:
        output_path = make_output_path(output_directory, base_path)
        output_file_name = make_output_file("stt", file_path.name, "txt")
    with file_path.open("rb") as f:
        audio_bytes = f.read()

    if language_code == "" or language_code is None:
        language_code = None

    transcription = client.speech_to_text.convert(
        model_id="scribe_v1",
        file=audio_bytes,
        language_code=language_code,
        enable_logging=True,
        diarize=diarize,
        tag_audio_events=True,
    )

    # Format transcript with speaker identification if diarization was enabled
    if diarize:
        formatted_transcript = format_diarized_transcript(transcription)
    else:
        formatted_transcript = transcription.text

    if return_transcript_to_client_directly:
        return TextContent(type="text", text=formatted_transcript)

    if save_transcript_to_file:
        transcript_bytes = formatted_transcript.encode("utf-8")

        # Handle different output modes
        success_message = f"Transcription saved to {file_path}"
        return handle_output_mode(
            transcript_bytes,
            output_path,
            output_file_name,
            output_mode,
            success_message,
        )

    # This should not be reached due to validation at the start of the function
    return TextContent(type="text", text="No output mode specified")


@mcp.tool(
    description=f"""Convert text description of a sound effect to sound effect with a given duration. {get_output_mode_description(output_mode)}.
    
    Duration must be between 0.5 and 5 seconds.

    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs. Only use when explicitly requested by the user.

    Args:
        text: Text description of the sound effect
        duration_seconds: Duration of the sound effect in seconds
        output_directory: Directory where files should be saved (only used when saving files).
            Defaults to $HOME/Desktop if not provided.
        loop: Whether to loop the sound effect. Defaults to False.
        output_format (str, optional): Output format of the generated audio. Formatted as codec_sample_rate_bitrate. So an mp3 with 22.05kHz sample rate at 32kbs is represented as mp3_22050_32. MP3 with 192kbps bitrate requires you to be subscribed to Creator tier or above. PCM with 44.1kHz sample rate requires you to be subscribed to Pro tier or above. Note that the μ-law format (sometimes written mu-law, often approximated as u-law) is commonly used for Twilio audio inputs.
            Defaults to "mp3_44100_128". Must be one of:
            mp3_22050_32
            mp3_44100_32
            mp3_44100_64
            mp3_44100_96
            mp3_44100_128
            mp3_44100_192
            pcm_8000
            pcm_16000
            pcm_22050
            pcm_24000
            pcm_44100
            ulaw_8000
            alaw_8000
            opus_48000_32
            opus_48000_64
            opus_48000_96
            opus_48000_128
            opus_48000_192
    """
)
def text_to_sound_effects(
    text: str,
    duration_seconds: float = 2.0,
    output_directory: str | None = None,
    output_format: str = "mp3_44100_128",
    loop: bool = False,
) -> Union[TextContent, EmbeddedResource]:
    if duration_seconds < 0.5 or duration_seconds > 5:
        make_error("Duration must be between 0.5 and 5 seconds")
    output_path = make_output_path(output_directory, base_path)
    output_file_name = make_output_file("sfx", text, "mp3")

    audio_data = client.text_to_sound_effects.convert(
        text=text,
        output_format=output_format,
        duration_seconds=duration_seconds,
        loop=loop,
    )
    audio_bytes = b"".join(audio_data)

    # Handle different output modes
    return handle_output_mode(audio_bytes, output_path, output_file_name, output_mode)


@mcp.tool(
    description="""
    Search for existing voices, a voice that has already been added to the user's ElevenLabs voice library.
    Searches in name, description, labels and category.

    Args:
        search: Search term to filter voices by. Searches in name, description, labels and category.
        sort: Which field to sort by. `created_at_unix` might not be available for older voices.
        sort_direction: Sort order, either ascending or descending.

    Returns:
        List of voices that match the search criteria.
    """
)
def search_voices(
    search: str | None = None,
    sort: Literal["created_at_unix", "name"] = "name",
    sort_direction: Literal["asc", "desc"] = "desc",
) -> list[McpVoice]:
    response = client.voices.search(
        search=search, sort=sort, sort_direction=sort_direction
    )
    return [
        McpVoice(id=voice.voice_id, name=voice.name, category=voice.category)
        for voice in response.voices
    ]


@mcp.tool(description="List all available models")
def list_models() -> list[McpModel]:
    response = client.models.list()
    return [
        McpModel(
            id=model.model_id,
            name=model.name,
            languages=[
                McpLanguage(language_id=lang.language_id, name=lang.name)
                for lang in model.languages
            ],
        )
        for model in response
    ]


@mcp.tool(description="Get details of a specific voice")
def get_voice(voice_id: str) -> McpVoice:
    """Get details of a specific voice."""
    response = client.voices.get(voice_id=voice_id)
    return McpVoice(
        id=response.voice_id,
        name=response.name,
        category=response.category,
        fine_tuning_status=response.fine_tuning.state,
    )


@mcp.tool(
    description="""Create an instant voice clone of a voice using provided audio files.

    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs. Only use when explicitly requested by the user.
    """
)
def voice_clone(
    name: str, files: list[str], description: str | None = None
) -> TextContent:
    input_files = [str(handle_input_file(file).absolute()) for file in files]
    voice = client.voices.ivc.create(
        name=name, description=description, files=input_files
    )

    return TextContent(
        type="text",
        text=f"""Voice cloned successfully: Name: {voice.name}
        ID: {voice.voice_id}
        Category: {voice.category}
        Description: {voice.description or "N/A"}""",
    )


@mcp.tool(
    description=f"""Isolate audio from a file. {get_output_mode_description(output_mode)}.

    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs. Only use when explicitly requested by the user.
    """
)
def isolate_audio(
    input_file_path: str, output_directory: str | None = None
) -> Union[TextContent, EmbeddedResource]:
    file_path = handle_input_file(input_file_path)
    output_path = make_output_path(output_directory, base_path)
    output_file_name = make_output_file("iso", file_path.name, "mp3")
    with file_path.open("rb") as f:
        audio_bytes = f.read()
    audio_data = client.audio_isolation.convert(
        audio=audio_bytes,
    )
    audio_bytes = b"".join(audio_data)

    # Handle different output modes
    return handle_output_mode(audio_bytes, output_path, output_file_name, output_mode)


@mcp.tool(
    description="Check the current subscription status. Could be used to measure the usage of the API."
)
def check_subscription() -> TextContent:
    subscription = client.user.subscription.get()
    return TextContent(type="text", text=f"{subscription.model_dump_json(indent=2)}")


@mcp.tool(
    description="""Create a conversational AI agent with custom configuration.

    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs. Only use when explicitly requested by the user.

    Args:
        name: Name of the agent
        first_message: First message the agent will say i.e. "Hi, how can I help you today?"
        system_prompt: System prompt for the agent
        voice_id: ID of the voice to use for the agent
        language: ISO 639-1 language code for the agent
        llm: LLM to use for the agent
        temperature: Temperature for the agent. The lower the temperature, the more deterministic the agent's responses will be. Range is 0 to 1.
        max_tokens: Maximum number of tokens to generate.
        asr_quality: Quality of the ASR. `high` or `low`.
        model_id: ID of the ElevenLabs model to use for the agent.
        optimize_streaming_latency: Optimize streaming latency. Range is 0 to 4.
        stability: Stability for the agent. Range is 0 to 1.
        similarity_boost: Similarity boost for the agent. Range is 0 to 1.
        turn_timeout: Timeout for the agent to respond in seconds. Defaults to 7 seconds.
        max_duration_seconds: Maximum duration of a conversation in seconds. Defaults to 600 seconds (10 minutes).
        record_voice: Whether to record the agent's voice.
        retention_days: Number of days to retain the agent's data.
    """
)
def create_agent(
    name: str,
    first_message: str,
    system_prompt: str,
    voice_id: str | None = DEFAULT_VOICE_ID,
    language: str = "en",
    llm: str = "gemini-2.0-flash-001",
    temperature: float = 0.5,
    max_tokens: int | None = None,
    asr_quality: str = "high",
    model_id: str = "eleven_turbo_v2",
    optimize_streaming_latency: int = 3,
    stability: float = 0.5,
    similarity_boost: float = 0.8,
    turn_timeout: int = 7,
    max_duration_seconds: int = 300,
    record_voice: bool = True,
    retention_days: int = 730,
) -> TextContent:
    conversation_config = create_conversation_config(
        language=language,
        system_prompt=system_prompt,
        llm=llm,
        first_message=first_message,
        temperature=temperature,
        max_tokens=max_tokens,
        asr_quality=asr_quality,
        voice_id=voice_id,
        model_id=model_id,
        optimize_streaming_latency=optimize_streaming_latency,
        stability=stability,
        similarity_boost=similarity_boost,
        turn_timeout=turn_timeout,
        max_duration_seconds=max_duration_seconds,
    )

    platform_settings = create_platform_settings(
        record_voice=record_voice,
        retention_days=retention_days,
    )

    response = client.conversational_ai.agents.create(
        name=name,
        conversation_config=conversation_config,
        platform_settings=platform_settings,
    )

    return TextContent(
        type="text",
        text=f"""Agent created successfully: Name: {name}, Agent ID: {response.agent_id}, System Prompt: {system_prompt}, Voice ID: {voice_id or "Default"}, Language: {language}, LLM: {llm}, You can use this agent ID for future interactions with the agent.""",
    )


@mcp.tool(
    description="""Add a knowledge base to ElevenLabs workspace. Allowed types are epub, pdf, docx, txt, html.

    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs. Only use when explicitly requested by the user.

    Args:
        agent_id: ID of the agent to add the knowledge base to.
        knowledge_base_name: Name of the knowledge base.
        url: URL of the knowledge base.
        input_file_path: Path to the file to add to the knowledge base.
        text: Text to add to the knowledge base.
    """
)
def add_knowledge_base_to_agent(
    agent_id: str,
    knowledge_base_name: str,
    url: str | None = None,
    input_file_path: str | None = None,
    text: str | None = None,
) -> TextContent:
    provided_params = [
        param for param in [url, input_file_path, text] if param is not None
    ]
    if len(provided_params) == 0:
        make_error("Must provide either a URL, a file, or text")
    if len(provided_params) > 1:
        make_error("Must provide exactly one of: URL, file, or text")

    if url is not None:
        response = client.conversational_ai.knowledge_base.documents.create_from_url(
            name=knowledge_base_name,
            url=url,
        )
    else:
        if text is not None:
            text_bytes = text.encode("utf-8")
            text_io = BytesIO(text_bytes)
            text_io.name = "text.txt"
            text_io.content_type = "text/plain"
            file = text_io
        elif input_file_path is not None:
            path = handle_input_file(
                file_path=input_file_path, audio_content_check=False
            )
            file = open(path, "rb")

        response = client.conversational_ai.knowledge_base.documents.create_from_file(
            name=knowledge_base_name,
            file=file,
        )

    agent = client.conversational_ai.agents.get(agent_id=agent_id)

    agent_config = agent.conversation_config.agent
    # agent_config is an object, not a dict, so convert it to dict
    agent_config_dict = agent_config.model_dump() if agent_config else {}
    knowledge_base_list = (
        agent_config_dict.get("prompt", {}).get("knowledge_base", []) if agent_config_dict else []
    )
    knowledge_base_list.append(
        KnowledgeBaseLocator(
            type="file" if file else "url",
            name=knowledge_base_name,
            id=response.id,
        )
    )

    if agent_config_dict and "prompt" not in agent_config_dict:
        agent_config_dict["prompt"] = {}
    if agent_config_dict:
        agent_config_dict["prompt"]["knowledge_base"] = knowledge_base_list

    client.conversational_ai.agents.update(
        agent_id=agent_id, conversation_config=agent.conversation_config
    )
    return TextContent(
        type="text",
        text=f"""Knowledge base created with ID: {response.id} and added to agent {agent_id} successfully.""",
    )


@mcp.tool(description="List all available conversational AI agents")
def list_agents() -> TextContent:
    """List all available conversational AI agents.

    Returns:
        TextContent with a formatted list of available agents
    """
    response = client.conversational_ai.agents.list()

    if not response.agents:
        return TextContent(type="text", text="No agents found.")

    agent_list = ",".join(
        f"{agent.name} (ID: {agent.agent_id})" for agent in response.agents
    )

    return TextContent(type="text", text=f"Available agents: {agent_list}")


@mcp.tool(description="Get details about a specific conversational AI agent")
def get_agent(agent_id: str) -> TextContent:
    """Get details about a specific conversational AI agent.

    Args:
        agent_id: The ID of the agent to retrieve

    Returns:
        TextContent with detailed information about the agent
    """
    response = client.conversational_ai.agents.get(agent_id=agent_id)

    voice_info = "None"
    if response.conversation_config.tts:
        voice_info = f"Voice ID: {response.conversation_config.tts.voice_id}"

    return TextContent(
        type="text",
        text=f"Agent Details: Name: {response.name}, Agent ID: {response.agent_id}, Voice Configuration: {voice_info}, Created At: {datetime.fromtimestamp(response.metadata.created_at_unix_secs).strftime('%Y-%m-%d %H:%M:%S')}",
    )


@mcp.tool(
    description="""Gets conversation with transcript. Returns: conversation details and full transcript. Use when: analyzing completed agent conversations.

    Args:
        conversation_id: The unique identifier of the conversation to retrieve, you can get the ids from the list_conversations tool.
    """
)
def get_conversation(
    conversation_id: str,
) -> TextContent:
    """Get conversation details with transcript"""
    try:
        response = client.conversational_ai.conversations.get(conversation_id)

        # Parse transcript using utility function
        transcript, _ = parse_conversation_transcript(response.transcript)

        response_text = f"""Conversation Details:
ID: {response.conversation_id}
Status: {response.status}
Agent ID: {response.agent_id}
Message Count: {len(response.transcript)}

Transcript:
{transcript}"""

        if response.metadata:
            metadata = response.metadata
            duration = getattr(
                metadata,
                "call_duration_secs",
                getattr(metadata, "duration_seconds", "N/A"),
            )
            started_at = getattr(
                metadata, "start_time_unix_secs", getattr(metadata, "started_at", "N/A")
            )
            response_text += (
                f"\n\nMetadata:\nDuration: {duration} seconds\nStarted: {started_at}"
            )

        if response.analysis:
            analysis_summary = getattr(
                response.analysis, "summary", "Analysis available but no summary"
            )
            response_text += f"\n\nAnalysis:\n{analysis_summary}"

        return TextContent(type="text", text=response_text)

    except Exception as e:
        make_error(f"Failed to fetch conversation: {str(e)}")
        # satisfies type checker
        return TextContent(type="text", text="")


@mcp.tool(
    description="""Lists agent conversations. Returns: conversation list with metadata. Use when: asked about conversation history.

    Args:
        agent_id (str, optional): Filter conversations by specific agent ID
        cursor (str, optional): Pagination cursor for retrieving next page of results
        call_start_before_unix (int, optional): Filter conversations that started before this Unix timestamp
        call_start_after_unix (int, optional): Filter conversations that started after this Unix timestamp
        page_size (int, optional): Number of conversations to return per page (1-100, defaults to 30)
        max_length (int, optional): Maximum character length of the response text (defaults to 10000)
    """
)
def list_conversations(
    agent_id: str | None = None,
    cursor: str | None = None,
    call_start_before_unix: int | None = None,
    call_start_after_unix: int | None = None,
    page_size: int = 30,
    max_length: int = 10000,
) -> TextContent:
    """List conversations with filtering options."""
    page_size = min(page_size, 100)

    try:
        response = client.conversational_ai.conversations.list(
            cursor=cursor,
            agent_id=agent_id,
            call_start_before_unix=call_start_before_unix,
            call_start_after_unix=call_start_after_unix,
            page_size=page_size,
        )

        if not response.conversations:
            return TextContent(type="text", text="No conversations found.")

        conv_list = []
        for conv in response.conversations:
            start_time = datetime.fromtimestamp(conv.start_time_unix_secs).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            conv_info = f"""Conversation ID: {conv.conversation_id}
Status: {conv.status}
Agent: {conv.agent_name or 'N/A'} (ID: {conv.agent_id})
Started: {start_time}
Duration: {conv.call_duration_secs} seconds
Messages: {conv.message_count}
Call Successful: {conv.call_successful}"""

            conv_list.append(conv_info)

        formatted_list = "\n\n".join(conv_list)

        pagination_info = f"Showing {len(response.conversations)} conversations"
        if response.has_more:
            pagination_info += f" (more available, next cursor: {response.next_cursor})"

        full_text = f"{pagination_info}\n\n{formatted_list}"

        # Use utility to handle large text content
        result_text = handle_large_text(full_text, max_length, "conversation list")

        # If content was saved to file, prepend pagination info
        if result_text != full_text:
            result_text = f"{pagination_info}\n\n{result_text}"

        return TextContent(type="text", text=result_text)

    except Exception as e:
        make_error(f"Failed to list conversations: {str(e)}")
        # This line is unreachable but satisfies type checker
        return TextContent(type="text", text="")


@mcp.tool(
    description=f"""Transform audio from one voice to another using provided audio files. {get_output_mode_description(output_mode)}.

    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs. Only use when explicitly requested by the user.
    """
)
def speech_to_speech(
    input_file_path: str,
    voice_name: str = "Adam",
    output_directory: str | None = None,
) -> Union[TextContent, EmbeddedResource]:
    voices = client.voices.search(search=voice_name)

    if len(voices.voices) == 0:
        make_error("No voice found with that name.")

    voice = next((v for v in voices.voices if v.name == voice_name), None)

    if voice is None:
        make_error(f"Voice with name: {voice_name} does not exist.")

    assert voice is not None  # Type assertion for type checker
    file_path = handle_input_file(input_file_path)
    output_path = make_output_path(output_directory, base_path)
    output_file_name = make_output_file("sts", file_path.name, "mp3")

    with file_path.open("rb") as f:
        audio_bytes = f.read()

    audio_data = client.speech_to_speech.convert(
        model_id="eleven_multilingual_sts_v2",
        voice_id=voice.voice_id,
        audio=audio_bytes,
    )

    audio_bytes = b"".join(audio_data)

    # Handle different output modes
    return handle_output_mode(audio_bytes, output_path, output_file_name, output_mode)


@mcp.tool(
    description=f"""Create voice previews from a text prompt. Creates three previews with slight variations. {get_output_mode_description(output_mode)}.
    
    If no text is provided, the tool will auto-generate text.

    Voice preview files are saved as: voice_design_(generated_voice_id)_(timestamp).mp3

    Example file name: voice_design_Ya2J5uIa5Pq14DNPsbC1_20250403_164949.mp3

    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs. Only use when explicitly requested by the user.
    """
)
def text_to_voice(
    voice_description: str,
    text: str | None = None,
    output_directory: str | None = None,
) -> list[EmbeddedResource] | TextContent:
    if voice_description == "":
        make_error("Voice description is required.")

    previews = client.text_to_voice.create_previews(
        voice_description=voice_description,
        text=text,
        auto_generate_text=True if text is None else False,
    )

    output_path = make_output_path(output_directory, base_path)

    generated_voice_ids = []
    results = []

    for preview in previews.previews:
        output_file_name = make_output_file(
            "voice_design", preview.generated_voice_id, "mp3", full_id=True
        )
        generated_voice_ids.append(preview.generated_voice_id)
        audio_bytes = base64.b64decode(preview.audio_base_64)

        # Handle different output modes
        result = handle_output_mode(
            audio_bytes, output_path, output_file_name, output_mode
        )
        results.append(result)

    # Use centralized multiple files output handling
    additional_info = f"Generated voice IDs are: {', '.join(generated_voice_ids)}"
    return handle_multiple_files_output_mode(results, output_mode, additional_info)


@mcp.tool(
    description="""Add a generated voice to the voice library. Uses the voice ID from the `text_to_voice` tool.

    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs. Only use when explicitly requested by the user.
    """
)
def create_voice_from_preview(
    generated_voice_id: str,
    voice_name: str,
    voice_description: str,
) -> TextContent:
    voice = client.text_to_voice.create_voice_from_preview(
        voice_name=voice_name,
        voice_description=voice_description,
        generated_voice_id=generated_voice_id,
    )

    return TextContent(
        type="text",
        text=f"Success. Voice created: {voice.name} with ID:{voice.voice_id}",
    )


def _get_phone_number_by_id(phone_number_id: str):
    """Helper function to get phone number details by ID."""
    phone_numbers = client.conversational_ai.phone_numbers.list()
    for phone in phone_numbers:
        if phone.phone_number_id == phone_number_id:
            return phone
    make_error(f"Phone number with ID {phone_number_id} not found.")


@mcp.tool(
    description="""Make an outbound call using an ElevenLabs agent. Automatically detects provider type (Twilio or SIP trunk) and uses the appropriate API.

    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs. Only use when explicitly requested by the user.

    Args:
        agent_id: The ID of the agent that will handle the call
        agent_phone_number_id: The ID of the phone number to use for the call
        to_number: The phone number to call (E.164 format: +1xxxxxxxxxx)

    Returns:
        TextContent containing information about the call
    """
)
def make_outbound_call(
    agent_id: str,
    agent_phone_number_id: str,
    to_number: str,
) -> TextContent:
    # Get phone number details to determine provider type
    phone_number = _get_phone_number_by_id(agent_phone_number_id)

    if phone_number.provider.lower() == "twilio":
        response = client.conversational_ai.twilio.outbound_call(
            agent_id=agent_id,
            agent_phone_number_id=agent_phone_number_id,
            to_number=to_number,
        )
        provider_info = "Twilio"
    elif phone_number.provider.lower() == "sip_trunk":
        response = client.conversational_ai.sip_trunk.outbound_call(
            agent_id=agent_id,
            agent_phone_number_id=agent_phone_number_id,
            to_number=to_number,
        )
        provider_info = "SIP trunk"
    else:
        make_error(f"Unsupported provider type: {phone_number.provider}")

    return TextContent(
        type="text", text=f"Outbound call initiated via {provider_info}: {response}."
    )


@mcp.tool(
    description="""Search for a voice across the entire ElevenLabs voice library.

    Args:
        page: Page number to return (0-indexed)
        page_size: Number of voices to return per page (1-100)
        search: Search term to filter voices by

    Returns:
        TextContent containing information about the shared voices
    """
)
def search_voice_library(
    page: int = 0,
    page_size: int = 10,
    search: str | None = None,
) -> TextContent:
    response = client.voices.get_shared(
        page=page,
        page_size=page_size,
        search=search,
    )

    if not response.voices:
        return TextContent(
            type="text", text="No shared voices found with the specified criteria."
        )

    voice_list = []
    for voice in response.voices:
        language_info = "N/A"
        if hasattr(voice, "verified_languages") and voice.verified_languages:
            languages = []
            for lang in voice.verified_languages:
                accent_info = (
                    f" ({lang.accent})"
                    if hasattr(lang, "accent") and lang.accent
                    else ""
                )
                languages.append(f"{lang.language}{accent_info}")
            language_info = ", ".join(languages)

        details = [
            f"Name: {voice.name}",
            f"ID: {voice.voice_id}",
            f"Category: {getattr(voice, 'category', 'N/A')}",
        ]
        # TODO: Make cleaner
        if hasattr(voice, "gender") and voice.gender:
            details.append(f"Gender: {voice.gender}")
        if hasattr(voice, "age") and voice.age:
            details.append(f"Age: {voice.age}")
        if hasattr(voice, "accent") and voice.accent:
            details.append(f"Accent: {voice.accent}")
        if hasattr(voice, "description") and voice.description:
            details.append(f"Description: {voice.description}")
        if hasattr(voice, "use_case") and voice.use_case:
            details.append(f"Use Case: {voice.use_case}")

        details.append(f"Languages: {language_info}")

        if hasattr(voice, "preview_url") and voice.preview_url:
            details.append(f"Preview URL: {voice.preview_url}")

        voice_info = "\n".join(details)
        voice_list.append(voice_info)

    formatted_info = "\n\n".join(voice_list)
    return TextContent(type="text", text=f"Shared Voices:\n\n{formatted_info}")


@mcp.tool(description="List all phone numbers associated with the ElevenLabs account")
def list_phone_numbers() -> TextContent:
    """List all phone numbers associated with the ElevenLabs account.

    Returns:
        TextContent containing formatted information about the phone numbers
    """
    response = client.conversational_ai.phone_numbers.list()

    if not response:
        return TextContent(type="text", text="No phone numbers found.")

    phone_info = []
    for phone in response:
        assigned_agent = "None"
        if phone.assigned_agent:
            assigned_agent = f"{phone.assigned_agent.agent_name} (ID: {phone.assigned_agent.agent_id})"

        phone_info.append(
            f"Phone Number: {phone.phone_number}\n"
            f"ID: {phone.phone_number_id}\n"
            f"Provider: {phone.provider}\n"
            f"Label: {phone.label}\n"
            f"Assigned Agent: {assigned_agent}"
        )

    formatted_info = "\n\n".join(phone_info)
    return TextContent(type="text", text=f"Phone Numbers:\n\n{formatted_info}")


@mcp.tool(description="Play an audio file. Supports WAV and MP3 formats.")
def play_audio(input_file_path: str) -> TextContent:
    file_path = handle_input_file(input_file_path)
    play(open(file_path, "rb").read(), use_ffmpeg=False)
    return TextContent(type="text", text=f"Successfully played audio file: {file_path}")


@mcp.tool(
    description="""Convert a prompt to music and save the output audio file to a given directory.
    Directory is optional, if not provided, the output file will be saved to $HOME/Desktop.

    Args:
        prompt: Prompt to convert to music. Must provide either prompt or composition_plan.
        output_directory: Directory to save the output audio file
        composition_plan: Composition plan to use for the music. Must provide either prompt or composition_plan.
        music_length_ms: Length of the generated music in milliseconds. Cannot be used if composition_plan is provided.

    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs. Only use when explicitly requested by the user."""
)
def compose_music(
    prompt: str | None = None,
    output_directory: str | None = None,
    composition_plan: MusicPrompt | None = None,
    music_length_ms: int | None = None,
) -> Union[TextContent, EmbeddedResource]:
    if prompt is None and composition_plan is None:
        make_error(
            f"Either prompt or composition_plan must be provided. Prompt: {prompt}"
        )

    if prompt is not None and composition_plan is not None:
        make_error("Only one of prompt or composition_plan must be provided")

    if music_length_ms is not None and composition_plan is not None:
        make_error("music_length_ms cannot be used if composition_plan is provided")

    output_path = make_output_path(output_directory, base_path)
    output_file_name = make_output_file("music", "", "mp3")

    audio_data = client.music.compose(
        prompt=prompt,
        music_length_ms=music_length_ms,
        composition_plan=composition_plan,
    )

    audio_bytes = b"".join(audio_data)

    # Handle different output modes
    return handle_output_mode(audio_bytes, output_path, output_file_name, output_mode)


@mcp.tool(
    description="""Create a composition plan for music generation. Usage of this endpoint does not cost any credits but is subject to rate limiting depending on your tier. Composition plans can be used when generating music with the compose_music tool.

    Args:
        prompt: Prompt to create a composition plan for
        music_length_ms: The length of the composition plan to generate in milliseconds. Must be between 10000ms and 300000ms. Optional - if not provided, the model will choose a length based on the prompt.
        source_composition_plan: An optional composition plan to use as a source for the new composition plan
    """
)
def create_composition_plan(
    prompt: str,
    music_length_ms: int | None = None,
    source_composition_plan: MusicPrompt | None = None,
) -> MusicPrompt:
    composition_plan = client.music.composition_plan.create(
        prompt=prompt,
        music_length_ms=music_length_ms,
        source_composition_plan=source_composition_plan,
    )

    return composition_plan


def main():
    print("Starting MCP server")
    """Run the MCP server"""
    mcp.run()


if __name__ == "__main__":
    main()
@mcp.tool(
    description="""Create a conversational AI agent from a template with pre-configured settings.

    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs. Only use when explicitly requested by the user.

    Args:
        name: Name of the agent
        template_type: Type of agent template to use
        custom_instructions: Custom instructions to override template defaults
        voice_id: ID of the voice to use for the agent (optional, will use template default)
        language: ISO 639-1 language code for the agent
        knowledge_base_source: Optional knowledge base source (URL, file path, or text)
"""
)
def create_agent_from_template(
    name: str,
    template_type: Literal["customer_service", "sales_assistant", "technical_support", "personal_assistant", "creative_writer", "educator", "therapist", "interviewer", "trainer"],
    custom_instructions: str | None = None,
    voice_id: str | None = None,
    language: str = "en",
    knowledge_base_source: str | None = None,
) -> TextContent:
    """Create a conversational AI agent from a predefined template."""
    
    # Template configurations
    templates = {
        "customer_service": {
            "system_prompt": """You are a helpful customer service representative. Always be polite, patient, and solution-focused. Listen carefully to customer concerns and provide clear, actionable assistance. Ask clarifying questions when needed and escalate complex issues to human agents when appropriate.""",
            "first_message": "Hello! I'm here to help you with any questions or concerns you might have. How can I assist you today?",
            "llm": "gemini-2.0-flash-001",
            "stability": 0.4,
            "similarity_boost": 0.8
        },
        "sales_assistant": {
            "system_prompt": """You are a knowledgeable sales assistant. Focus on understanding customer needs, providing valuable information about products or services, and guiding customers through their purchasing decisions. Be consultative rather than pushy, and always prioritize customer value.""",
            "first_message": "Hi there! I'd love to help you find exactly what you're looking for. What brings you here today?",
            "llm": "gemini-2.0-flash-001",
            "stability": 0.5,
            "similarity_boost": 0.8
        },
        "technical_support": {
            "system_prompt": """You are a technical support specialist. Diagnose technical issues systematically, provide step-by-step troubleshooting instructions, and explain technical concepts in clear, understandable terms. Always ask relevant questions to narrow down the problem.""",
            "first_message": "I'm here to help resolve any technical issues you're experiencing. Can you describe the problem you're encountering?",
            "llm": "gemini-2.0-flash-001",
            "stability": 0.3,
            "similarity_boost": 0.7
        },
        "personal_assistant": {
            "system_prompt": """You are a helpful personal assistant. Assist with scheduling, information lookup, task management, and general productivity. Be organized, proactive, and anticipate needs. Provide helpful suggestions and reminders.""",
            "first_message": "Hello! I'm your personal assistant. How can I help you stay organized and productive today?",
            "llm": "gemini-2.0-flash-001",
            "stability": 0.6,
            "similarity_boost": 0.8
        },
        "creative_writer": {
            "system_prompt": """You are a creative writing assistant. Help brainstorm ideas, develop characters and plots, provide writing feedback, and inspire creativity. Be imaginative, supportive, and constructive in your suggestions.""",
            "first_message": "Hello! I'm here to help with your creative writing projects. What story, character, or idea would you like to develop?",
            "llm": "gemini-2.0-flash-001",
            "stability": 0.8,
            "similarity_boost": 0.9
        },
        "educator": {
            "system_prompt": """You are a knowledgeable educator. Explain concepts clearly, adapt your teaching style to the learner's level, encourage questions, and provide examples and analogies to enhance understanding. Be patient and encouraging.""",
            "first_message": "Hello! I'm here to help you learn. What subject would you like to explore or what concepts would you like me to explain?",
            "llm": "gemini-2.0-flash-001",
            "stability": 0.5,
            "similarity_boost": 0.8
        },
        "therapist": {
            "system_prompt": """You are a supportive therapeutic conversation partner. Provide emotional support, help process feelings, offer perspective, and encourage self-reflection. Be empathetic, non-judgmental, and focus on the person's wellbeing. Remember you are not a replacement for professional therapy.""",
            "first_message": "Hello. I'm here to listen and support you. How are you feeling today?",
            "llm": "gemini-2.0-flash-001",
            "stability": 0.7,
            "similarity_boost": 0.9
        },
        "interviewer": {
            "system_prompt": """You are a skilled interviewer. Ask thoughtful, open-ended questions, actively listen to responses, and follow up appropriately. Create a comfortable environment for meaningful conversation and extract valuable insights.""",
            "first_message": "Hello! I'm excited to learn more about you and your experiences. Let's start with some questions - are you ready?",
            "llm": "gemini-2.0-flash-001",
            "stability": 0.4,
            "similarity_boost": 0.7
        },
        "trainer": {
            "system_prompt": """You are a fitness and wellness trainer. Provide motivation, create workout plans, offer nutritional advice, track progress, and encourage healthy lifestyle choices. Be supportive, knowledgeable, and adapt programs to individual needs and limitations.""",
            "first_message": "Hello! I'm here to help you achieve your fitness and wellness goals. What would you like to work on today?",
            "llm": "gemini-2.0-flash-001",
            "stability": 0.6,
            "similarity_boost": 0.8
        }
    }
    
    if template_type not in templates:
        make_error(f"Template type '{template_type}' is not supported.")
    
    template = templates[template_type]
    
    # Use custom instructions if provided, otherwise use template
    system_prompt = custom_instructions or template["system_prompt"]
    first_message = template["first_message"]
    llm = template["llm"]
    stability = template["stability"]
    similarity_boost = template["similarity_boost"]
    
    # Create the agent
    conversation_config = create_conversation_config(
        language=language,
        system_prompt=system_prompt,
        llm=llm,
        first_message=first_message,
        temperature=0.7,
        max_tokens=None,
        asr_quality="high",
        voice_id=voice_id,
        model_id="eleven_turbo_v2",
        optimize_streaming_latency=3,
        stability=stability,
        similarity_boost=similarity_boost,
        turn_timeout=7,
        max_duration_seconds=300,
    )

    platform_settings = create_platform_settings(
        record_voice=True,
        retention_days=730,
    )

    response = client.conversational_ai.agents.create(
        name=name,
        conversation_config=conversation_config,
        platform_settings=platform_settings,
    )
    
    result_message = f"""Agent created successfully from '{template_type}' template: 
Name: {name}
Agent ID: {response.agent_id}
Template Type: {template_type}
System Prompt: {system_prompt}
Voice ID: {voice_id or "Default"}
Language: {language}
LLM: {llm}

You can use this agent ID for future interactions with the agent."""

    # Add knowledge base if source provided
    if knowledge_base_source:
        try:
            if knowledge_base_source.startswith(('http://', 'https://')):
                # URL
                add_knowledge_base_to_agent(
                    agent_id=response.agent_id,
                    knowledge_base_name=f"{template_type.title()} Knowledge Base",
                    url=knowledge_base_source
                )
                result_message += f"\n\nKnowledge base added from URL: {knowledge_base_source}"
            elif os.path.isfile(knowledge_base_source):
                # File
                add_knowledge_base_to_agent(
                    agent_id=response.agent_id,
                    knowledge_base_name=f"{template_type.title()} Knowledge Base",
                    file_path=knowledge_base_source
                )
                result_message += f"\n\nKnowledge base added from file: {knowledge_base_source}"
            else:
                # Text
                add_knowledge_base_to_agent(
                    agent_id=response.agent_id,
                    knowledge_base_name=f"{template_type.title()} Knowledge Base",
                    text=knowledge_base_source
                )
                result_message += f"\n\nKnowledge base added from provided text."
        except Exception as e:
            result_message += f"\n\nWarning: Failed to add knowledge base: {str(e)}"

    return TextContent(type="text", text=result_message)@mcp.tool(
    description="""Analyze conversational AI agent performance and provide insights.

    This tool analyzes conversation data to provide metrics like:
    - Average conversation duration
    - Response satisfaction patterns  
    - Common conversation topics
    - Agent performance indicators
    - Recommendations for improvement

    Args:
        agent_id: The ID of the agent to analyze
        days_back: Number of days to analyze (default: 30)
        min_conversations: Minimum number of conversations needed for analysis (default: 5)
"""
)
def analyze_agent_performance(
    agent_id: str,
    days_back: int = 30,
    min_conversations: int = 5,
) -> TextContent:
    """Analyze agent performance based on conversation history."""
    
    # Calculate date range
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    start_unix = int(start_date.timestamp())
    end_unix = int(end_date.timestamp())
    
    try:
        # Get conversations for the agent
        response = client.conversational_ai.conversations.list(
            agent_id=agent_id,
            call_start_after_unix=start_unix,
            call_start_before_unix=end_unix,
            page_size=100,
        )
        
        if not response.conversations:
            return TextContent(
                type="text", 
                text=f"No conversations found for agent {agent_id} in the last {days_back} days."
            )
        
        conversations = response.conversations
        
        if len(conversations) < min_conversations:
            return TextContent(
                type="text", 
                text=f"Only {len(conversations)} conversations found (minimum {min_conversations} required for analysis)."
            )
        
        # Analyze conversations
        total_conversations = len(conversations)
        successful_calls = sum(1 for conv in conversations if conv.call_successful)
        avg_duration = sum(conv.call_duration_secs for conv in conversations) / total_conversations
        avg_messages = sum(conv.message_count for conv in conversations) / total_conversations
        
        # Calculate success rate
        success_rate = (successful_calls / total_conversations) * 100
        
        # Analyze conversation status distribution
        status_counts = {}
        for conv in conversations:
            status = conv.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Performance indicators
        performance_score = min(100, (success_rate * 0.6) + (min(100, avg_duration/300 * 100) * 0.2) + (min(100, avg_messages/20 * 100) * 0.2))
        
        analysis_text = f"""Agent Performance Analysis (Last {days_back} days):

📊 CONVERSATION METRICS
• Total Conversations: {total_conversations}
• Successful Calls: {successful_calls} ({success_rate:.1f}%)
• Average Duration: {avg_duration:.1f} seconds ({avg_duration/60:.1f} minutes)
• Average Messages per Conversation: {avg_messages:.1f}

📈 STATUS BREAKDOWN
"""
        
        for status, count in status_counts.items():
            percentage = (count / total_conversations) * 100
            analysis_text += f"• {status.title()}: {count} ({percentage:.1f}%)\n"
        
        analysis_text += f"""
🎯 PERFORMANCE SCORE: {performance_score:.1f}/100

💡 INSIGHTS & RECOMMENDATIONS
"""
        
        # Generate recommendations based on metrics
        recommendations = []
        
        if success_rate < 70:
            recommendations.append("• Consider improving agent configuration or voice quality to reduce call failures")
        elif success_rate > 90:
            recommendations.append("• Excellent success rate - your agent configuration is working well")
            
        if avg_duration < 60:
            recommendations.append("• Conversations are quite short - consider if agents are being cut off too early")
        elif avg_duration > 900:  # 15 minutes
            recommendations.append("• Long conversation durations - consider if this indicates good engagement or inefficient routing")
            
        if avg_messages < 5:
            recommendations.append("• Low message count suggests quick resolutions or potential engagement issues")
        elif avg_messages > 50:
            recommendations.append("• High message count suggests good engagement and thorough conversations")
        
        if not recommendations:
            recommendations.append("• Performance metrics look healthy - continue monitoring")
        
        for rec in recommendations:
            analysis_text += f"{rec}\n"
        
        analysis_text += f"""
📋 DETAILED STATISTICS
• Analysis Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
• Conversations Analyzed: {total_conversations}
• Minimum Threshold: {min_conversations} conversations
• Performance Score: {performance_score:.1f}/100
"""
        
        return TextContent(type="text", text=analysis_text)
        
    except Exception as e:
        make_error(f"Failed to analyze agent performance: {str(e)}")
        return TextContent(type="text", text="")@mcp.tool(
    description="""Update an existing conversational AI agent with new configuration.

    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs. Only use when explicitly requested by the user.

    Args:
        agent_id: The ID of the agent to update
        new_name: New name for the agent (optional)
        new_system_prompt: New system prompt (optional)
        new_voice_id: New voice ID to use (optional)
        new_language: New language code (optional)
        new_temperature: New temperature setting (0-1, optional)
        new_stability: New stability setting (0-1, optional)
        new_similarity_boost: New similarity boost setting (0-1, optional)
        update_first_message: Whether to update the first message (requires first_message parameter)
        first_message: New first message (optional)
"""
)
def update_agent(
    agent_id: str,
    new_name: str | None = None,
    new_system_prompt: str | None = None,
    new_voice_id: str | None = None,
    new_language: str | None = None,
    new_temperature: float | None = None,
    new_stability: float | None = None,
    new_similarity_boost: float | None = None,
    update_first_message: bool = False,
    first_message: str | None = None,
) -> TextContent:
    """Update an existing conversational AI agent."""
    
    try:
        # Get current agent configuration
        current_agent = client.conversational_ai.agents.get(agent_id=agent_id)
        
        # Build new configuration
        current_config = current_agent.conversation_config
        
        # Update system prompt if provided
        if new_system_prompt:
            if "prompt" not in current_config["agent"]:
                current_config["agent"]["prompt"] = {}
            current_config["agent"]["prompt"]["prompt"] = new_system_prompt
        
        # Update temperature if provided
        if new_temperature is not None:
            if "prompt" not in current_config["agent"]:
                current_config["agent"]["prompt"] = {}
            current_config["agent"]["prompt"]["temperature"] = new_temperature
        
        # Update language if provided
        if new_language:
            current_config["agent"]["language"] = new_language
        
        # Update TTS settings if voice or stability/similarity settings provided
        if new_voice_id or new_stability is not None or new_similarity_boost is not None:
            if "tts" not in current_config:
                current_config["tts"] = {}
            
            if new_voice_id:
                current_config["tts"]["voice_id"] = new_voice_id
            if new_stability is not None:
                current_config["tts"]["stability"] = new_stability
            if new_similarity_boost is not None:
                current_config["tts"]["similarity_boost"] = new_similarity_boost
        
        # Update first message if requested and provided
        if update_first_message and first_message:
            current_config["agent"]["first_message"] = first_message
        
        # Update the agent
        response = client.conversational_ai.agents.update(
            agent_id=agent_id,
            conversation_config=current_config,
        )
        
        # Update name if provided
        if new_name:
            agent_info = response.model_dump()
            agent_info["name"] = new_name
            response = client.conversational_ai.agents.update(
                agent_id=agent_id,
                name=new_name,
                conversation_config=current_config,
            )
        
        update_summary = f"Agent updated successfully:\n"
        update_summary += f"Agent ID: {agent_id}\n"
        
        if new_name:
            update_summary += f"New Name: {new_name}\n"
        if new_system_prompt:
            update_summary += "System Prompt: Updated\n"
        if new_voice_id:
            update_summary += f"Voice ID: {new_voice_id}\n"
        if new_language:
            update_summary += f"Language: {new_language}\n"
        if new_temperature is not None:
            update_summary += f"Temperature: {new_temperature}\n"
        if new_stability is not None:
            update_summary += f"Stability: {new_stability}\n"
        if new_similarity_boost is not None:
            update_summary += f"Similarity Boost: {new_similarity_boost}\n"
        if update_first_message and first_message:
            update_summary += "First Message: Updated\n"
        
        update_summary += "\nNote: Some changes may take a few minutes to take effect."
        
        return TextContent(type="text", text=update_summary)
        
    except Exception as e:
        make_error(f"Failed to update agent: {str(e)}")
        return TextContent(type="text", text="")@mcp.tool(
    description="""Generate a comprehensive conversation analytics report for one or more agents.

    ⚠️ COST WARNING: This tool makes multiple API calls to ElevenLabs which may incur costs. Only use when explicitly requested by the user.

    Args:
        agent_ids: Comma-separated list of agent IDs to analyze (or 'all' for all agents)
        days_back: Number of days to analyze (default: 30)
        output_directory: Directory where the report should be saved (optional)
        report_format: Format for the report ('json', 'csv', 'summary') - default: 'summary'
"""
)
def generate_conversation_analytics_report(
    agent_ids: str,
    days_back: int = 30,
    output_directory: str | None = None,
    report_format: Literal["json", "csv", "summary"] = "summary",
) -> Union[TextContent, EmbeddedResource]:
    """Generate comprehensive conversation analytics report."""
    
    from datetime import datetime, timedelta
    import json
    import csv
    from io import StringIO
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    start_unix = int(start_date.timestamp())
    end_unix = int(end_date.timestamp())
    
    try:
        # Get all agents if 'all' specified
        if agent_ids.lower() == 'all':
            all_agents = client.conversational_ai.agents.list()
            agent_list = [agent.agent_id for agent in all_agents.agents]
        else:
            agent_list = [aid.strip() for aid in agent_ids.split(',')]
        
        # Initialize report data
        report_data = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "analysis_period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "days": days_back
                },
                "agents_analyzed": agent_list,
                "total_agents": len(agent_list)
            },
            "summary": {},
            "agent_details": {},
            "conversation_metrics": {}
        }
        
        total_conversations = 0
        total_successful = 0
        total_duration = 0
        total_messages = 0
        
        # Analyze each agent
        for agent_id in agent_list:
            try:
                # Get agent info
                agent_info = client.conversational_ai.agents.get(agent_id=agent_id)
                
                # Get conversations
                conversations = client.conversational_ai.conversations.list(
                    agent_id=agent_id,
                    call_start_after_unix=start_unix,
                    call_start_before_unix=end_unix,
                    page_size=100,
                )
                
                conv_list = conversations.conversations
                if not conv_list:
                    continue
                
                # Calculate metrics for this agent
                agent_conversations = len(conv_list)
                agent_successful = sum(1 for conv in conv_list if conv.call_successful)
                agent_avg_duration = sum(conv.call_duration_secs for conv in conv_list) / agent_conversations
                agent_avg_messages = sum(conv.message_count for conv in conv_list) / agent_conversations
                agent_success_rate = (agent_successful / agent_conversations) * 100 if agent_conversations > 0 else 0
                
                # Status distribution
                status_dist = {}
                for conv in conv_list:
                    status = conv.status
                    status_dist[status] = status_dist.get(status, 0) + 1
                
                # Store agent details
                report_data["agent_details"][agent_id] = {
                    "agent_name": agent_info.name,
                    "conversations": {
                        "total": agent_conversations,
                        "successful": agent_successful,
                        "success_rate": agent_success_rate,
                        "avg_duration_seconds": agent_avg_duration,
                        "avg_duration_minutes": agent_avg_duration / 60,
                        "avg_messages": agent_avg_messages,
                        "status_distribution": status_dist
                    }
                }
                
                # Add to totals
                total_conversations += agent_conversations
                total_successful += agent_successful
                total_duration += sum(conv.call_duration_secs for conv in conv_list)
                total_messages += sum(conv.message_count for conv in conv_list)
                
            except Exception as e:
                report_data["agent_details"][agent_id] = {"error": str(e)}
        
        # Calculate overall summary
        overall_success_rate = (total_successful / total_conversations * 100) if total_conversations > 0 else 0
        overall_avg_duration = (total_duration / total_conversations) if total_conversations > 0 else 0
        overall_avg_messages = (total_messages / total_conversations) if total_conversations > 0 else 0
        
        report_data["summary"] = {
            "total_conversations": total_conversations,
            "total_successful_calls": total_successful,
            "overall_success_rate": overall_success_rate,
            "overall_avg_duration_seconds": overall_avg_duration,
            "overall_avg_duration_minutes": overall_avg_duration / 60,
            "overall_avg_messages": overall_avg_messages,
            "agents_with_data": len([aid for aid in agent_list if aid in report_data["agent_details"]])
        }
        
        # Format report based on requested format
        if report_format == "json":
            report_text = json.dumps(report_data, indent=2, default=str)
            file_extension = "json"
            
        elif report_format == "csv":
            # Create CSV output
            output = StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "Agent ID", "Agent Name", "Total Conversations", "Successful Calls", 
                "Success Rate (%)", "Avg Duration (min)", "Avg Messages"
            ])
            
            # Write agent data
            for agent_id, details in report_data["agent_details"].items():
                if "error" not in details:
                    conv_data = details["conversations"]
                    writer.writerow([
                        agent_id,
                        details["agent_name"],
                        conv_data["total"],
                        conv_data["successful"],
                        f"{conv_data['success_rate']:.1f}",
                        f"{conv_data['avg_duration_minutes']:.1f}",
                        f"{conv_data['avg_messages']:.1f}"
                    ])
            
            report_text = output.getvalue()
            file_extension = "csv"
            
        else:  # summary format
            report_lines = [
                f"📊 CONVERSATION ANALYTICS REPORT",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({days_back} days)",
                "",
                f"🎯 OVERALL SUMMARY",
                f"• Total Conversations: {total_conversations:,}",
                f"• Successful Calls: {total_successful:,} ({overall_success_rate:.1f}%)",
                f"• Average Duration: {overall_avg_duration:.1f}s ({overall_avg_duration/60:.1f} min)",
                f"• Average Messages: {overall_avg_messages:.1f}",
                f"• Agents Analyzed: {report_data['summary']['agents_with_data']}",
                "",
                "📋 AGENT BREAKDOWN"
            ]
            
            for agent_id, details in report_data["agent_details"].items():
                if "error" not in details:
                    conv_data = details["conversations"]
                    report_lines.extend([
                        f"• {details['agent_name']} ({agent_id})",
                        f"  - Conversations: {conv_data['total']} (Success: {conv_data['successful']}, {conv_data['success_rate']:.1f}%)",
                        f"  - Avg Duration: {conv_data['avg_duration_minutes']:.1f} min, Messages: {conv_data['avg_messages']:.1f}",
                        ""
                    ])
                else:
                    report_lines.extend([
                        f"• {agent_id}: Error - {details['error']}",
                        ""
                    ])
            
            report_text = "\n".join(report_lines)
            file_extension = "txt"
        
        # Save and return based on output mode
        output_path = make_output_path(output_directory, base_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"conversation_analytics_{timestamp}.{file_extension}"
        
        report_bytes = report_text.encode('utf-8')
        
        return handle_output_mode(
            report_bytes, 
            output_path, 
            filename, 
            output_mode,
            f"Conversation analytics report generated: {total_conversations} conversations analyzed"
        )
        
    except Exception as e:
        make_error(f"Failed to generate conversation analytics report: {str(e)}")
        return TextContent(type="text", text="")@mcp.tool(
    description="""Manage the lifecycle of conversational AI agents (create, update, delete, duplicate).

    Args:
        action: Action to perform ('create', 'update', 'delete', 'duplicate', 'list')
        agent_id: Agent ID for update/delete/duplicate actions (required for these actions)
        new_name: New name for the agent (for create/update actions)
        new_description: Description for the agent (optional)
        copy_settings_from: Agent ID to copy settings from (for create action)
"""
)
def manage_agent_lifecycle(
    action: Literal["create", "update", "delete", "duplicate", "list"],
    agent_id: str | None = None,
    new_name: str | None = None,
    new_description: str | None = None,
    copy_settings_from: str | None = None,
) -> TextContent:
    """Manage the lifecycle of conversational AI agents."""
    
    try:
        if action == "list":
            # List all agents
            response = client.conversational_ai.agents.list()
            
            if not response.agents:
                return TextContent(type="text", text="No agents found in your account.")
            
            agent_info = []
            agent_info.append("🤖 CONVERSATIONAL AI AGENTS")
            agent_info.append(f"Total: {len(response.agents)} agents")
            agent_info.append("")
            
            for agent in response.agents:
                # Get agent details for additional info
                try:
                    details = client.conversational_ai.agents.get(agent.agent_id)
                    created_date = datetime.fromtimestamp(details.metadata.created_at_unix_secs).strftime('%Y-%m-%d')
                    
                    agent_info.append(f"• {agent.name}")
                    agent_info.append(f"  ID: {agent.agent_id}")
                    agent_info.append(f"  Created: {created_date}")
                    
                    # Try to get recent conversation count
                    try:
                        recent_convs = client.conversational_ai.conversations.list(
                            agent_id=agent.agent_id,
                            page_size=1
                        )
                        if recent_convs.conversations:
                            agent_info.append(f"  Recent Activity: Yes")
                        else:
                            agent_info.append(f"  Recent Activity: No conversations yet")
                    except:
                        agent_info.append(f"  Recent Activity: Unknown")
                    
                    agent_info.append("")
                    
                except Exception as e:
                    agent_info.append(f"• {agent.name} (ID: {agent.agent_id}) - Error loading details: {str(e)}")
                    agent_info.append("")
            
            return TextContent(type="text", text="\n".join(agent_info))
        
        elif action == "delete":
            if not agent_id:
                make_error("Agent ID is required for delete action.")
            
            # Confirm deletion
            agent_info = client.conversational_ai.agents.get(agent_id)
            agent_name = agent_info.name
            
            try:
                client.conversational_ai.agents.delete(agent_id)
                return TextContent(
                    type="text", 
                    text=f"✅ Agent '{agent_name}' (ID: {agent_id}) has been deleted successfully."
                )
            except Exception as e:
                make_error(f"Failed to delete agent: {str(e)}")
        
        elif action == "duplicate":
            if not agent_id:
                make_error("Agent ID is required for duplicate action.")
            if not new_name:
                make_error("New name is required for duplicate action.")
            
            # Get original agent
            original_agent = client.conversational_ai.agents.get(agent_id)
            original_config = original_agent.conversation_config
            
            # Create new agent with copied settings
            new_agent = client.conversational_ai.agents.create(
                name=new_name,
                conversation_config=original_config,
                platform_settings=create_platform_settings(record_voice=True, retention_days=730),
            )
            
            return TextContent(
                type="text",
                text=f"✅ Agent duplicated successfully!\n"
                     f"Original: {original_agent.name} (ID: {agent_id})\n"
                     f"Duplicate: {new_agent.name} (ID: {new_agent.agent_id})\n"
                     f"All settings and configurations have been copied."
            )
        
        elif action == "create":
            if not new_name:
                make_error("Name is required for create action.")
            
            # Copy settings from another agent if specified
            if copy_settings_from:
                try:
                    source_agent = client.conversational_ai.agents.get(copy_settings_from)
                    source_config = source_agent.conversation_config
                    
                    # Update agent name in config if needed
                    if "agent" in source_config and "first_message" in source_config["agent"]:
                        # Update first message to include new name
                        source_config["agent"]["first_message"] = f"Hello! I'm {new_name}, your AI assistant. How can I help you today?"
                    
                    new_agent = client.conversational_ai.agents.create(
                        name=new_name,
                        conversation_config=source_config,
                        platform_settings=create_platform_settings(record_voice=True, retention_days=730),
                    )
                    
                    return TextContent(
                        type="text",
                        text=f"✅ Agent created successfully by copying settings!\n"
                             f"Source: {source_agent.name} (ID: {copy_settings_from})\n"
                             f"New Agent: {new_agent.name} (ID: {new_agent.agent_id})\n"
                             f"All configurations have been copied and adapted."
                    )
                    
                except Exception as e:
                    make_error(f"Failed to copy settings from agent {copy_settings_from}: {str(e)}")
            
            else:
                # Create basic agent
                basic_config = create_conversation_config(
                    language="en",
                    system_prompt="You are a helpful AI assistant. Be friendly, professional, and solution-focused.",
                    llm="gemini-2.0-flash-001",
                    first_message="Hello! I'm your AI assistant. How can I help you today?",
                    temperature=0.7,
                    max_tokens=None,
                    asr_quality="high",
                    voice_id=DEFAULT_VOICE_ID,
                    model_id="eleven_turbo_v2",
                    optimize_streaming_latency=3,
                    stability=0.5,
                    similarity_boost=0.8,
                    turn_timeout=7,
                    max_duration_seconds=300,
                )
                
                new_agent = client.conversational_ai.agents.create(
                    name=new_name,
                    conversation_config=basic_config,
                    platform_settings=create_platform_settings(record_voice=True, retention_days=730),
                )
                
                return TextContent(
                    type="text",
                    text=f"✅ Agent created successfully!\n"
                         f"Name: {new_agent.name}\n"
                         f"Agent ID: {new_agent.agent_id}\n"
                         f"Configuration: Basic conversational AI agent ready for customization."
                )
        
        elif action == "update":
            if not agent_id:
                make_error("Agent ID is required for update action.")
            
            # This is a simplified update - in practice you'd want more granular controls
            agent_info = client.conversational_ai.agents.get(agent_id)
            
            if new_name:
                # Update name
                current_config = agent_info.conversation_config
                updated_agent = client.conversational_ai.agents.update(
                    agent_id=agent_id,
                    name=new_name,
                    conversation_config=current_config,
                )
                
                return TextContent(
                    type="text",
                    text=f"✅ Agent updated successfully!\n"
                         f"Old Name: {agent_info.name}\n"
                         f"New Name: {new_name}\n"
                         f"Agent ID: {agent_id}"
                )
            else:
                make_error("At least one update parameter (name, description, etc.) is required.")
        
        else:
            make_error(f"Unsupported action: {action}")
            
    except Exception as e:
        make_error(f"Failed to manage agent lifecycle: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# ADDITIONAL VOICE MANAGEMENT TOOLS
# ============================================================================

@mcp.tool(description="Edit an existing voice with new name, description, or labels")
def edit_voice(
    voice_id: str,
    name: str | None = None,
    description: str | None = None,
    labels: dict | None = None,
) -> TextContent:
    """Edit voice details."""
    try:
        updated_voice = client.voices.edit(
            voice_id=voice_id,
            name=name,
            description=description,
            labels=labels,
        )
        return TextContent(
            type="text",
            text=f"Voice updated successfully: {updated_voice.name} (ID: {updated_voice.voice_id})"
        )
    except Exception as e:
        make_error(f"Failed to edit voice: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get settings for a specific voice")
def get_voice_settings(voice_id: str) -> TextContent:
    """Get voice settings."""
    try:
        settings = client.voices.get_settings(voice_id=voice_id)
        return TextContent(type="text", text=f"{settings.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to get voice settings: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get default voice settings")
def get_default_voice_settings() -> TextContent:
    """Get default voice settings."""
    try:
        settings = client.voices.get_default_settings()
        return TextContent(type="text", text=f"{settings.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to get default voice settings: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(
    description=f"""Delete a voice from the library. {get_output_mode_description(output_mode)}.""",
)
def delete_voice(voice_id: str, output_directory: str | None = None) -> TextContent:
    """Delete a voice."""
    try:
        client.voices.delete(voice_id=voice_id)
        return TextContent(type="text", text=f"Voice {voice_id} deleted successfully.")
    except Exception as e:
        make_error(f"Failed to delete voice: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# HISTORY MANAGEMENT TOOLS
# ============================================================================

@mcp.tool(description="Get generation history with pagination")
def get_history(
    page_size: int = 100,
    start_after_history_item_id: str | None = None,
) -> TextContent:
    """Get generation history."""
    try:
        response = client.history.get(
            page_size=page_size,
            start_after_history_item_id=start_after_history_item_id,
        )
        
        history_info = []
        history_info.append(f"History Items: {len(response.history)}")
        
        for item in response.history:
            history_info.append(f"ID: {item.history_item_id}")
            history_info.append(f"File Name: {item.file_name}")
            history_info.append(f"Content Type: {item.content_type}")
            history_info.append(f"Date: {datetime.fromtimestamp(item.date_unix_secs).strftime('%Y-%m-%d %H:%M:%S')}")
            history_info.append("")
        
        return TextContent(type="text", text="\n".join(history_info))
    except Exception as e:
        make_error(f"Failed to get history: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get details of a specific history item")
def get_history_item(history_item_id: str) -> TextContent:
    """Get history item details."""
    try:
        response = client.history.get_item(history_item_id=history_item_id)
        return TextContent(type="text", text=f"{response.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to get history item: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(
    description=f"""Get audio from a history item. {get_output_mode_description(output_mode)}.""",
)
def get_history_item_audio(
    history_item_id: str,
    output_directory: str | None = None,
) -> Union[TextContent, EmbeddedResource]:
    """Get history item audio."""
    try:
        output_path = make_output_path(output_directory, base_path)
        output_file_name = make_output_file("history", history_item_id, "mp3")
        
        audio_data = client.history.get_item_audio(
            history_item_id=history_item_id,
        )
        audio_bytes = b"".join(audio_data)
        
        return handle_output_mode(
            audio_bytes, output_path, output_file_name, output_mode
        )
    except Exception as e:
        make_error(f"Failed to get history item audio: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Delete a history item")
def delete_history_item(history_item_id: str) -> TextContent:
    """Delete history item."""
    try:
        client.history.delete(history_item_id=history_item_id)
        return TextContent(type="text", text=f"History item {history_item_id} deleted successfully.")
    except Exception as e:
        make_error(f"Failed to delete history item: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(
    description=f"""Download multiple history items as a zip file. {get_output_mode_description(output_mode)}.""",
)
def download_history_items(
    history_item_ids: list[str],
    output_directory: str | None = None,
) -> Union[TextContent, EmbeddedResource]:
    """Download history items."""
    try:
        output_path = make_output_path(output_directory, base_path)
        output_file_name = "history_download.zip"
        
        audio_data = client.history.download(history_item_ids=history_item_ids)
        audio_bytes = b"".join(audio_data)
        
        return handle_output_mode(
            audio_bytes, output_path, output_file_name, output_mode
        )
    except Exception as e:
        make_error(f"Failed to download history items: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# PRONUNCIATION DICTIONARIES TOOLS
# ============================================================================

@mcp.tool(description="List all pronunciation dictionaries")
def list_pronunciation_dictionaries() -> TextContent:
    """List pronunciation dictionaries."""
    try:
        response = client.pronunciation_dictionaries.list()
        
        dict_info = []
        dict_info.append(f"Pronunciation Dictionaries: {len(response.pronunciation_dictionaries)}")
        
        for dictionary in response.pronunciation_dictionaries:
            dict_info.append(f"Name: {dictionary.name}")
            dict_info.append(f"ID: {dictionary.pronunciation_dictionary_id}")
            dict_info.append(f"Description: {dictionary.description or 'N/A'}")
            dict_info.append("")
        
        return TextContent(type="text", text="\n".join(dict_info))
    except Exception as e:
        make_error(f"Failed to list pronunciation dictionaries: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get details of a specific pronunciation dictionary")
def get_pronunciation_dictionary(dictionary_id: str) -> TextContent:
    """Get pronunciation dictionary."""
    try:
        response = client.pronunciation_dictionaries.get(
            pronunciation_dictionary_id=dictionary_id
        )
        return TextContent(type="text", text=f"{response.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to get pronunciation dictionary: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(
    description="""Create pronunciation dictionary from rules.
    
    Args:
        name: Name of the dictionary
        description: Optional description
        rules: List of pronunciation rules in format {"IPA": "word", "text": "pronunciation"}
    """
)
def create_pronunciation_dictionary_from_rules(
    name: str,
    description: str | None = None,
    rules: list[dict] | None = None,
) -> TextContent:
    """Create pronunciation dictionary from rules."""
    try:
        response = client.pronunciation_dictionaries.add(
            name=name,
            description=description,
            rules=rules or [],
        )
        return TextContent(
            type="text",
            text=f"Pronunciation dictionary created: {response.name} (ID: {response.pronunciation_dictionary_id})"
        )
    except Exception as e:
        make_error(f"Failed to create pronunciation dictionary: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(
    description="""Add rules to an existing pronunciation dictionary.
    
    Args:
        dictionary_id: ID of the dictionary
        rules: List of pronunciation rules in format {"IPA": "word", "text": "pronunciation"}
    """
)
def add_pronunciation_rules(dictionary_id: str, rules: list[dict]) -> TextContent:
    """Add pronunciation rules."""
    try:
        response = client.pronunciation_dictionaries.add_rules(
            pronunciation_dictionary_id=dictionary_id,
            rules=rules,
        )
        return TextContent(
            type="text",
            text=f"Added {len(rules)} rules to dictionary {dictionary_id}"
        )
    except Exception as e:
        make_error(f"Failed to add pronunciation rules: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(
    description="""Remove rules from a pronunciation dictionary.
    
    Args:
        dictionary_id: ID of the dictionary
        rule_strings: List of rule strings to remove
    """
)
def remove_pronunciation_rules(dictionary_id: str, rule_strings: list[str]) -> TextContent:
    """Remove pronunciation rules."""
    try:
        response = client.pronunciation_dictionaries.remove_rules(
            pronunciation_dictionary_id=dictionary_id,
            rule_strings=rule_strings,
        )
        return TextContent(
            type="text",
            text=f"Removed {len(rule_strings)} rules from dictionary {dictionary_id}"
        )
    except Exception as e:
        make_error(f"Failed to remove pronunciation rules: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# STUDIO PROJECTS TOOLS
# ============================================================================

@mcp.tool(description="List all Studio projects")
def list_studio_projects() -> TextContent:
    """List Studio projects."""
    try:
        response = client.studio.list_projects()
        
        project_info = []
        project_info.append(f"Studio Projects: {len(response.projects)}")
        
        for project in response.projects:
            project_info.append(f"Name: {project.name}")
            project_info.append(f"ID: {project.project_id}")
            project_info.append(f"Created: {datetime.fromtimestamp(project.created_at_unix_secs).strftime('%Y-%m-%d %H:%M:%S')}")
            project_info.append("")
        
        return TextContent(type="text", text="\n".join(project_info))
    except Exception as e:
        make_error(f"Failed to list Studio projects: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Create a new Studio project")
def create_studio_project(name: str, description: str | None = None) -> TextContent:
    """Create Studio project."""
    try:
        response = client.studio.create_project(
            name=name,
            description=description,
        )
        return TextContent(
            type="text",
            text=f"Studio project created: {response.name} (ID: {response.project_id})"
        )
    except Exception as e:
        make_error(f"Failed to create Studio project: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get details of a Studio project")
def get_studio_project(project_id: str) -> TextContent:
    """Get Studio project."""
    try:
        response = client.studio.get_project(project_id=project_id)
        return TextContent(type="text", text=f"{response.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to get Studio project: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Delete a Studio project")
def delete_studio_project(project_id: str) -> TextContent:
    """Delete Studio project."""
    try:
        client.studio.delete_project(project_id=project_id)
        return TextContent(type="text", text=f"Studio project {project_id} deleted successfully.")
    except Exception as e:
        make_error(f"Failed to delete Studio project: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# ADDITIONAL CONVERSATION TOOLS
# ============================================================================

@mcp.tool(description="Delete a conversation")
def delete_conversation(conversation_id: str) -> TextContent:
    """Delete conversation."""
    try:
        client.conversational_ai.conversations.delete(conversation_id)
        return TextContent(type="text", text=f"Conversation {conversation_id} deleted successfully.")
    except Exception as e:
        make_error(f"Failed to delete conversation: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(
    description=f"""Get audio from a conversation. {get_output_mode_description(output_mode)}.""",
)
def get_conversation_audio(
    conversation_id: str,
    output_directory: str | None = None,
) -> Union[TextContent, EmbeddedResource]:
    """Get conversation audio."""
    try:
        output_path = make_output_path(output_directory, base_path)
        output_file_name = make_output_file("conversation", conversation_id, "mp3")
        
        audio_data = client.conversational_ai.conversations.get_audio(
            conversation_id=conversation_id,
        )
        audio_bytes = b"".join(audio_data)
        
        return handle_output_mode(
            audio_bytes, output_path, output_file_name, output_mode
        )
    except Exception as e:
        make_error(f"Failed to get conversation audio: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get signed URL for conversation")
def get_conversation_signed_url(agent_id: str) -> TextContent:
    """Get conversation signed URL."""
    try:
        response = client.conversational_ai.conversations.get_signed_url(
            agent_id=agent_id,
        )
        return TextContent(type="text", text=f"{response.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to get conversation signed URL: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get conversation token")
def get_conversation_token(agent_id: str) -> TextContent:
    """Get conversation token."""
    try:
        response = client.conversational_ai.conversations.get_token(
            agent_id=agent_id,
        )
        return TextContent(type="text", text=f"{response.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to get conversation token: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Send feedback for a conversation")
def send_conversation_feedback(conversation_id: str, feedback: bool) -> TextContent:
    """Send conversation feedback."""
    try:
        client.conversational_ai.conversations.send_feedback(
            conversation_id=conversation_id,
            feedback=feedback,
        )
        return TextContent(type="text", text=f"Feedback {'positive' if feedback else 'negative'} sent for conversation {conversation_id}.")
    except Exception as e:
        make_error(f"Failed to send conversation feedback: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# PHONE NUMBER MANAGEMENT TOOLS
# ============================================================================

@mcp.tool(description="Create/import a phone number")
def create_phone_number(
    phone_number: str,
    provider_type: Literal["twilio", "sip_trunk"],
    label: str | None = None,
) -> TextContent:
    """Create phone number."""
    try:
        response = client.conversational_ai.phone_numbers.create(
            phone_number=phone_number,
            provider_type=provider_type,
            label=label,
        )
        return TextContent(
            type="text",
            text=f"Phone number created: {response.phone_number} (ID: {response.phone_number_id})"
        )
    except Exception as e:
        make_error(f"Failed to create phone number: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get details of a phone number")
def get_phone_number(phone_number_id: str) -> TextContent:
    """Get phone number."""
    try:
        response = client.conversational_ai.phone_numbers.get(
            phone_number_id=phone_number_id
        )
        return TextContent(type="text", text=f"{response.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to get phone number: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Update a phone number")
def update_phone_number(
    phone_number_id: str,
    label: str | None = None,
    provider_type: Literal["twilio", "sip_trunk"] | None = None,
) -> TextContent:
    """Update phone number."""
    try:
        response = client.conversational_ai.phone_numbers.update(
            phone_number_id=phone_number_id,
            label=label,
            provider_type=provider_type,
        )
        return TextContent(
            type="text",
            text=f"Phone number updated: {response.phone_number} (ID: {response.phone_number_id})"
        )
    except Exception as e:
        make_error(f"Failed to update phone number: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Delete a phone number")
def delete_phone_number(phone_number_id: str) -> TextContent:
    """Delete phone number."""
    try:
        client.conversational_ai.phone_numbers.delete(phone_number_id)
        return TextContent(type="text", text=f"Phone number {phone_number_id} deleted successfully.")
    except Exception as e:
        make_error(f"Failed to delete phone number: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# TOOLS MANAGEMENT
# ============================================================================

@mcp.tool(description="List all tools available in the workspace")
def list_tools() -> TextContent:
    """List all tools in workspace."""
    try:
        response = client.conversational_ai.tools.list()

        tools_info = []
        tools_info.append(f"Tools: {len(response.tools)}")
        tools_info.append("")

        for tool in response.tools:
            tools_info.append(f"Name: {tool.name}")
            tools_info.append(f"ID: {tool.tool_id}")
            tools_info.append(f"Type: {tool.type}")
            tools_info.append(f"Description: {tool.description}")
            tools_info.append("")

        return TextContent(type="text", text="\n".join(tools_info))
    except Exception as e:
        make_error(f"Failed to list tools: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get details of a specific tool")
def get_tool(tool_id: str) -> TextContent:
    """Get tool details."""
    try:
        response = client.conversational_ai.tools.get(tool_id=tool_id)
        return TextContent(type="text", text=f"{response.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to get tool: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Update a tool configuration")
def update_tool(tool_id: str, tool_config: dict) -> TextContent:
    """Update tool configuration."""
    try:
        response = client.conversational_ai.tools.update(
            tool_id=tool_id,
            tool_config=tool_config,
        )
        return TextContent(type="text", text=f"Tool {tool_id} updated successfully.\n{response.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to update tool: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Delete a tool from the workspace")
def delete_tool(tool_id: str) -> TextContent:
    """Delete tool."""
    try:
        client.conversational_ai.tools.delete(tool_id=tool_id)
        return TextContent(type="text", text=f"Tool {tool_id} deleted successfully.")
    except Exception as e:
        make_error(f"Failed to delete tool: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get agents that depend on a specific tool")
def get_tool_dependent_agents(tool_id: str) -> TextContent:
    """Get agents that depend on this tool."""
    try:
        response = client.conversational_ai.tools.get_dependent_agents(tool_id=tool_id)

        if not response.agents:
            return TextContent(type="text", text=f"No agents depend on tool {tool_id}")

        agents_info = []
        agents_info.append(f"Agents depending on tool {tool_id}:")
        agents_info.append("")

        for agent in response.agents:
            agents_info.append(f"Agent ID: {agent.agent_id}")
            agents_info.append(f"Agent Name: {agent.name}")
            agents_info.append("")

        return TextContent(type="text", text="\n".join(agents_info))
    except Exception as e:
        make_error(f"Failed to get dependent agents: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# KNOWLEDGE BASE MANAGEMENT TOOLS
# ============================================================================

@mcp.tool(description="List all knowledge base documents")
def list_knowledge_base_documents() -> TextContent:
    """List knowledge base documents."""
    try:
        response = client.conversational_ai.knowledge_base.list()
        
        doc_info = []
        doc_info.append(f"Knowledge Base Documents: {len(response.documents)}")
        
        for doc in response.documents:
            doc_info.append(f"Name: {doc.name}")
            doc_info.append(f"ID: {doc.document_id}")
            doc_info.append(f"Type: {doc.type}")
            doc_info.append("")
        
        return TextContent(type="text", text="\n".join(doc_info))
    except Exception as e:
        make_error(f"Failed to list knowledge base documents: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get a knowledge base document")
def get_knowledge_base_document(document_id: str) -> TextContent:
    """Get knowledge base document."""
    try:
        response = client.conversational_ai.knowledge_base.get_document(
            document_id=document_id
        )
        return TextContent(type="text", text=f"{response.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to get knowledge base document: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Create knowledge base from URL")
def create_knowledge_base_from_url(url: str, name: str) -> TextContent:
    """Create knowledge base from URL."""
    try:
        response = client.conversational_ai.knowledge_base.create_from_url(
            name=name,
            url=url,
        )
        return TextContent(
            type="text",
            text=f"Knowledge base created from URL: {response.name} (ID: {response.document_id})"
        )
    except Exception as e:
        make_error(f"Failed to create knowledge base from URL: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Create knowledge base from text")
def create_knowledge_base_from_text(name: str, text: str) -> TextContent:
    """Create knowledge base from text."""
    try:
        # Convert text to file-like object
        text_bytes = text.encode("utf-8")
        text_io = BytesIO(text_bytes)
        text_io.name = "text.txt"
        text_io.content_type = "text/plain"

        response = client.conversational_ai.knowledge_base.documents.create_from_file(
            name=name,
            file=text_io,
        )
        return TextContent(
            type="text",
            text=f"Knowledge base created from text: {response.name} (ID: {response.document_id})"
        )
    except Exception as e:
        make_error(f"Failed to create knowledge base from text: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Delete a knowledge base document")
def delete_knowledge_base_document(document_id: str) -> TextContent:
    """Delete knowledge base document."""
    try:
        client.conversational_ai.knowledge_base.delete_document(document_id)
        return TextContent(type="text", text=f"Knowledge base document {document_id} deleted successfully.")
    except Exception as e:
        make_error(f"Failed to delete knowledge base document: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Update a knowledge base document name")
def update_knowledge_base_document(document_id: str, name: str) -> TextContent:
    """Update knowledge base document name."""
    try:
        response = client.conversational_ai.knowledge_base.documents.update(
            documentation_id=document_id,
            name=name,
        )
        return TextContent(
            type="text",
            text=f"Knowledge base document {document_id} updated successfully.\n{response.model_dump_json(indent=2)}"
        )
    except Exception as e:
        make_error(f"Failed to update knowledge base document: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Create knowledge base document from file")
def create_knowledge_base_document_from_file(
    file_path: str,
    name: str | None = None,
) -> TextContent:
    """Create knowledge base document from file."""
    try:
        # Validate file exists
        input_file_path = handle_input_file(file_path)

        with open(input_file_path, "rb") as f:
            response = client.conversational_ai.knowledge_base.documents.create_from_file(
                file=f,
                name=name,
            )

        return TextContent(
            type="text",
            text=f"Knowledge base created from file: {response.name} (ID: {response.document_id})"
        )
    except Exception as e:
        make_error(f"Failed to create knowledge base from file: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get content of a knowledge base document")
def get_document_content(document_id: str) -> TextContent:
    """Get document content."""
    try:
        response = client.conversational_ai.knowledge_base.documents.get_content(
            documentation_id=document_id
        )

        # The response should contain the document content
        return TextContent(
            type="text",
            text=f"Document {document_id} content:\n\n{response}"
        )
    except Exception as e:
        make_error(f"Failed to get document content: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get a specific chunk from a knowledge base document")
def get_document_chunk(document_id: str, chunk_id: str) -> TextContent:
    """Get document chunk."""
    try:
        response = client.conversational_ai.knowledge_base.documents.chunk.get(
            documentation_id=document_id,
            chunk_id=chunk_id,
        )
        return TextContent(type="text", text=f"{response.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to get document chunk: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get total size of knowledge base documents")
def get_knowledge_base_size() -> TextContent:
    """Get knowledge base size."""
    try:
        response = client.conversational_ai.knowledge_base.get_size()

        # Format the size in a human-readable format
        size_bytes = response.size_bytes if hasattr(response, 'size_bytes') else 0
        size_mb = size_bytes / (1024 * 1024)

        return TextContent(
            type="text",
            text=f"Knowledge base size: {size_bytes:,} bytes ({size_mb:.2f} MB)"
        )
    except Exception as e:
        make_error(f"Failed to get knowledge base size: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get agents that depend on a knowledge base document")
def get_document_dependent_agents(document_id: str) -> TextContent:
    """Get agents that depend on this document."""
    try:
        response = client.conversational_ai.knowledge_base.documents.get_agents(
            documentation_id=document_id
        )

        if not response.agents:
            return TextContent(type="text", text=f"No agents depend on document {document_id}")

        agents_info = []
        agents_info.append(f"Agents depending on document {document_id}:")
        agents_info.append("")

        for agent in response.agents:
            agents_info.append(f"Agent ID: {agent.agent_id}")
            agents_info.append(f"Agent Name: {agent.name}")
            agents_info.append("")

        return TextContent(type="text", text="\n".join(agents_info))
    except Exception as e:
        make_error(f"Failed to get dependent agents: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# RAG INDEX MANAGEMENT TOOLS
# ============================================================================

@mcp.tool(description="Compute RAG index for a knowledge base document")
def compute_rag_index(
    document_id: str,
    model: str = "e5_mistral_7b_instruct",
) -> TextContent:
    """Compute RAG index for document.

    Args:
        document_id: The document ID
        model: Embedding model (e5_mistral_7b_instruct or multilingual_e5_large_instruct)
    """
    try:
        response = client.conversational_ai.knowledge_base.document.compute_rag_index(
            documentation_id=document_id,
            model=model,
        )
        return TextContent(
            type="text",
            text=f"RAG index computation started for document {document_id}.\n{response.model_dump_json(indent=2)}"
        )
    except Exception as e:
        make_error(f"Failed to compute RAG index: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get RAG indexes for a knowledge base document")
def get_rag_index(document_id: str) -> TextContent:
    """Get RAG indexes for document."""
    try:
        response = client.conversational_ai.get_document_rag_indexes(
            documentation_id=document_id
        )

        if not response.indexes:
            return TextContent(type="text", text=f"No RAG indexes found for document {document_id}")

        index_info = []
        index_info.append(f"RAG Indexes for document {document_id}:")
        index_info.append("")

        for idx in response.indexes:
            index_info.append(f"Index ID: {idx.id}")
            index_info.append(f"Model: {idx.model}")
            index_info.append(f"Status: {idx.status}")
            index_info.append(f"Progress: {idx.progress_percentage}%")
            index_info.append("")

        return TextContent(type="text", text="\n".join(index_info))
    except Exception as e:
        make_error(f"Failed to get RAG indexes: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get overview of all RAG indexes in the workspace")
def get_rag_index_overview() -> TextContent:
    """Get RAG index overview."""
    try:
        response = client.conversational_ai.rag_index_overview()
        return TextContent(type="text", text=f"{response.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to get RAG index overview: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Delete a RAG index for a knowledge base document")
def delete_rag_index(document_id: str, rag_index_id: str) -> TextContent:
    """Delete RAG index."""
    try:
        client.conversational_ai.delete_document_rag_index(
            documentation_id=document_id,
            rag_index_id=rag_index_id,
        )
        return TextContent(
            type="text",
            text=f"RAG index {rag_index_id} deleted successfully from document {document_id}."
        )
    except Exception as e:
        make_error(f"Failed to delete RAG index: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# AUDIO NATIVE TOOLS
# ============================================================================

@mcp.tool(description="Create an Audio Native project")
def create_audio_native_project(name: str, description: str | None = None) -> TextContent:
    """Create Audio Native project."""
    try:
        response = client.audio_native.create_project(
            name=name,
            description=description,
        )
        return TextContent(
            type="text",
            text=f"Audio Native project created: {response.name} (ID: {response.project_id})"
        )
    except Exception as e:
        make_error(f"Failed to create Audio Native project: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# WEBHOOK TOOLS
# ============================================================================

@mcp.tool(description="List all webhooks")
def list_webhooks() -> TextContent:
    """List webhooks."""
    try:
        response = client.webhooks.list()
        
        webhook_info = []
        webhook_info.append(f"Webhooks: {len(response.webhooks)}")
        
        for webhook in response.webhooks:
            webhook_info.append(f"URL: {webhook.url}")
            webhook_info.append(f"ID: {webhook.webhook_id}")
            webhook_info.append(f"Status: {webhook.status}")
            webhook_info.append("")
        
        return TextContent(type="text", text="\n".join(webhook_info))
    except Exception as e:
        make_error(f"Failed to list webhooks: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# FORCED ALIGNMENT TOOLS
# ============================================================================

@mcp.tool(
    description=f"""Align audio with transcript text. {get_output_mode_description(output_mode)}.""",
)
def create_forced_alignment(
    audio_file_path: str,
    transcript: str,
    output_directory: str | None = None,
) -> Union[TextContent, EmbeddedResource]:
    """Create forced alignment."""
    try:
        file_path = handle_input_file(audio_file_path)
        output_path = make_output_path(output_directory, base_path)
        output_file_name = make_output_file("alignment", file_path.name, "json")
        
        with file_path.open("rb") as f:
            audio_bytes = f.read()
        
        alignment_data = client.alignment.convert(
            audio=audio_bytes,
            transcript=transcript,
        )
        alignment_bytes = alignment_data.model_dump_json().encode('utf-8')
        
        return handle_output_mode(
            alignment_bytes, output_path, output_file_name, output_mode
        )
    except Exception as e:
        make_error(f"Failed to create forced alignment: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# ADDITIONAL AGENT TOOLS
# ============================================================================

@mcp.tool(description="Duplicate an existing agent to create a new one")
def duplicate_agent(agent_id: str, name: str | None = None) -> TextContent:
    """Duplicate agent.

    Args:
        agent_id: The ID of the agent to duplicate
        name: Optional new name for the duplicated agent
    """
    try:
        response = client.conversational_ai.agents.duplicate(
            agent_id=agent_id,
            name=name,
        )
        return TextContent(
            type="text",
            text=f"Agent duplicated successfully. New agent ID: {response.agent_id}"
        )
    except Exception as e:
        make_error(f"Failed to duplicate agent: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Get agent link for conversation")
def get_agent_link(agent_id: str) -> TextContent:
    """Get agent link."""
    try:
        response = client.conversational_ai.agents.link.get(agent_id=agent_id)
        return TextContent(type="text", text=f"{response.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to get agent link: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Simulate a conversation with an agent")
def simulate_conversation(
    agent_id: str,
    simulation_specification: dict,
    extra_evaluation_criteria: list[dict] | None = None,
    new_turns_limit: int | None = None,
) -> TextContent:
    """Simulate conversation.

    Args:
        agent_id: The agent ID
        simulation_specification: Must include simulated_user_config. Minimal example:
            {"simulated_user_config": {"prompt": {"prompt": "You are a customer asking about services"}}}
        extra_evaluation_criteria: Optional additional evaluation criteria
        new_turns_limit: Optional limit on number of conversation turns
    """
    try:
        response = client.conversational_ai.agents.simulate_conversation(
            agent_id=agent_id,
            simulation_specification=simulation_specification,
            extra_evaluation_criteria=extra_evaluation_criteria,
            new_turns_limit=new_turns_limit,
        )
        return TextContent(type="text", text=f"{response.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to simulate conversation: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Simulate a conversation with streaming response")
def stream_simulate_conversation(
    agent_id: str,
    simulation_specification: dict,
    extra_evaluation_criteria: list[dict] | None = None,
    new_turns_limit: int | None = None,
) -> TextContent:
    """Simulate conversation with streaming.

    Args:
        agent_id: The agent ID
        simulation_specification: Must include simulated_user_config. Minimal example:
            {"simulated_user_config": {"prompt": {"prompt": "You are a customer asking about services"}}}
        extra_evaluation_criteria: Optional additional evaluation criteria
        new_turns_limit: Optional limit on number of conversation turns
    """
    try:
        response = client.conversational_ai.agents.simulate_conversation_stream(
            agent_id=agent_id,
            simulation_specification=simulation_specification,
            extra_evaluation_criteria=extra_evaluation_criteria,
            new_turns_limit=new_turns_limit,
        )

        # Collect the streamed response
        result_parts = []
        for chunk in response:
            if chunk:
                result_parts.append(str(chunk))

        return TextContent(
            type="text",
            text="Conversation simulation completed:\n\n" + "\n".join(result_parts)
        )
    except Exception as e:
        make_error(f"Failed to stream simulate conversation: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Calculate LLM usage for an agent")
def calculate_llm_usage(agent_id: str, days_back: int = 30) -> TextContent:
    """Calculate LLM usage."""
    try:
        response = client.conversational_ai.agents.calculate_llm_usage(
            agent_id=agent_id,
            days_back=days_back,
        )
        return TextContent(type="text", text=f"{response.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to calculate LLM usage: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# USER INFO TOOLS
# ============================================================================

@mcp.tool(description="Get current user information")
def get_user_info() -> TextContent:
    """Get user info."""
    try:
        response = client.user.get()
        return TextContent(type="text", text=f"{response.model_dump_json(indent=2)}")
    except Exception as e:
        make_error(f"Failed to get user info: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# ENHANCED TTS TOOLS WITH TIMESTAMPS
# ============================================================================

@mcp.tool(
    description=f"""Convert text to speech with character-level timestamps. {get_output_mode_description(output_mode)}.""",
)
def text_to_speech_with_timestamps(
    text: str,
    voice_id: str | None = None,
    model_id: str = "eleven_turbo_v2",
    output_directory: str | None = None,
    language: str = "en",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0,
    use_speaker_boost: bool = True,
    speed: float = 1.0,
    output_format: str = "mp3_44100_128",
) -> Union[TextContent, EmbeddedResource]:
    """Convert text to speech with timestamps."""
    try:
        if text == "":
            make_error("Text is required.")
        
        voice = None
        if voice_id is None:
            voice_id = DEFAULT_VOICE_ID
        else:
            voice = client.voices.get(voice_id=voice_id)
        
        output_path = make_output_path(output_directory, base_path)
        output_file_name = make_output_file("tts_ts", text, "json")
        
        tts_data = client.text_to_speech_with_timestamps.convert(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            output_format=output_format,
            voice_settings={
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style,
                "use_speaker_boost": use_speaker_boost,
                "speed": speed,
            },
        )
        
        # Extract timestamps data
        if hasattr(tts_data, 'timestamps'):
            timestamps_data = tts_data.timestamps
        else:
            timestamps_data = tts_data
        
        timestamps_bytes = str(timestamps_data).encode('utf-8')
        
        return handle_output_mode(
            timestamps_bytes, output_path, output_file_name, output_mode
        )
    except Exception as e:
        make_error(f"Failed to generate TTS with timestamps: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# STREAMLINED VOICE MANAGEMENT
# ============================================================================

@mcp.tool(
    description=f"""Stream text to speech for real-time playback. {get_output_mode_description(output_mode)}.""",
)
def text_to_speech_stream(
    text: str,
    voice_id: str | None = None,
    model_id: str = "eleven_turbo_v2",
    output_directory: str | None = None,
    language: str = "en",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
) -> Union[TextContent, EmbeddedResource]:
    """Stream text to speech."""
    try:
        if text == "":
            make_error("Text is required.")
        
        voice = None
        if voice_id is None:
            voice_id = DEFAULT_VOICE_ID
        else:
            voice = client.voices.get(voice_id=voice_id)
        
        output_path = make_output_path(output_directory, base_path)
        output_file_name = make_output_file("tts_stream", text, "mp3")
        
        audio_data = client.text_to_speech.stream(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            voice_settings={
                "stability": stability,
                "similarity_boost": similarity_boost,
            },
        )
        audio_bytes = b"".join(audio_data)
        
        return handle_output_mode(
            audio_bytes, output_path, output_file_name, output_mode
        )
    except Exception as e:
        make_error(f"Failed to stream TTS: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# ADVANCED VOICE CLONING TOOLS
# ============================================================================

@mcp.tool(
    description="""Clone voice from multiple audio files with advanced settings.
    
    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs.
    
    Args:
        name: Name of the cloned voice
        files: List of audio file paths
        description: Optional description
        labels: Optional labels dictionary
        category: Voice category (e.g., 'voicebook', 'generated')
    """
)
def advanced_voice_clone(
    name: str,
    files: list[str],
    description: str | None = None,
    labels: dict | None = None,
    category: str | None = None,
) -> TextContent:
    """Advanced voice cloning with additional options."""
    try:
        input_files = [str(handle_input_file(file).absolute()) for file in files]
        voice = client.voices.add(
            name=name,
            description=description,
            files=input_files,
            labels=labels,
            category=category,
        )
        
        return TextContent(
            type="text",
            text=f"""Voice cloned successfully: Name: {voice.name}
ID: {voice.voice_id}
Category: {voice.category}
Description: {voice.description or "N/A"}""",
        )
    except Exception as e:
        make_error(f"Failed to clone voice: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# ENHANCED AUDIO PROCESSING TOOLS
# ============================================================================

@mcp.tool(
    description=f"""Enhanced audio isolation with quality settings. {get_output_mode_description(output_mode)}.
    
    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs.
    """
)
def enhanced_audio_isolation(
    input_file_path: str,
    output_directory: str | None = None,
    isolation_level: str = "balanced",
) -> Union[TextContent, EmbeddedResource]:
    """Enhanced audio isolation."""
    try:
        file_path = handle_input_file(input_file_path)
        output_path = make_output_path(output_directory, base_path)
        output_file_name = make_output_file("enhanced_iso", file_path.name, "mp3")
        
        with file_path.open("rb") as f:
            audio_bytes = f.read()
        
        audio_data = client.audio_isolation.convert(
            audio=audio_bytes,
            isolation_level=isolation_level,
        )
        audio_bytes = b"".join(audio_data)
        
        return handle_output_mode(
            audio_bytes, output_path, output_file_name, output_mode
        )
    except Exception as e:
        make_error(f"Failed to isolate audio: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(
    description=f"""Enhanced sound effects with duration and style options. {get_output_mode_description(output_mode)}.
    
    ⚠️ COST WARNING: This tool makes an API call to ElevenLabs which may incur costs.
    """
)
def enhanced_sound_effects(
    text: str,
    duration_seconds: float = 2.0,
    output_directory: str | None = None,
    output_format: str = "mp3_44100_128",
    style: str = "realistic",
    intensity: float = 0.7,
) -> Union[TextContent, EmbeddedResource]:
    """Enhanced sound effects generation."""
    try:
        if duration_seconds < 0.5 or duration_seconds > 5:
            make_error("Duration must be between 0.5 and 5 seconds")
        
        output_path = make_output_path(output_directory, base_path)
        output_file_name = make_output_file("enhanced_sfx", text, "mp3")
        
        audio_data = client.text_to_sound_effects.convert(
            text=text,
            output_format=output_format,
            duration_seconds=duration_seconds,
            style=style,
            intensity=intensity,
        )
        audio_bytes = b"".join(audio_data)
        
        return handle_output_mode(
            audio_bytes, output_path, output_file_name, output_mode
        )
    except Exception as e:
        make_error(f"Failed to generate enhanced sound effects: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# BATCH PROCESSING TOOLS
# ============================================================================

@mcp.tool(
    description=f"""Process multiple text files with batch text-to-speech. {get_output_mode_description(output_mode)}.
    
    ⚠️ COST WARNING: This tool makes multiple API calls to ElevenLabs which may incur costs.
    
    Args:
        input_directory: Directory containing text files
        voice_id: Voice ID to use (uses default if not specified)
        output_directory: Where to save the audio files
    """
)
def batch_text_to_speech(
    input_directory: str,
    voice_id: str | None = None,
    output_directory: str | None = None,
    model_id: str = "eleven_turbo_v2",
) -> TextContent:
    """Batch process text files to speech."""
    try:
        if voice_id is None:
            voice_id = DEFAULT_VOICE_ID
        
        input_path = Path(input_directory)
        if not input_path.exists() or not input_path.is_dir():
            make_error(f"Input directory {input_directory} does not exist or is not a directory")
        
        output_path = make_output_path(output_directory, base_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        text_files = list(input_path.glob("*.txt")) + list(input_path.glob("*.md"))
        if not text_files:
            make_error("No .txt or .md files found in the input directory")
        
        results = []
        for text_file in text_files:
            try:
                with open(text_file, 'r', encoding='utf-8') as f:
                    text_content = f.read().strip()
                
                if text_content:
                    # Generate audio for this text
                    audio_data = client.text_to_speech.convert(
                        text=text_content,
                        voice_id=voice_id,
                        model_id=model_id,
                        voice_settings={
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                        },
                    )
                    audio_bytes = b"".join(audio_data)
                    
                    # Save to output directory
                    output_file = output_path / f"{text_file.stem}.mp3"
                    with open(output_file, 'wb') as f:
                        f.write(audio_bytes)
                    
                    results.append(f"✓ {text_file.name} -> {output_file.name}")
                else:
                    results.append(f"⚠ {text_file.name} (empty file)")
            
            except Exception as e:
                results.append(f"✗ {text_file.name} (error: {str(e)})")
        
        return TextContent(
            type="text",
            text=f"Batch TTS completed for {len(text_files)} files:\n" + "\n".join(results)
        )
    except Exception as e:
        make_error(f"Failed to process batch TTS: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# QUALITY ANALYSIS TOOLS
# ============================================================================

@mcp.tool(description="Analyze voice quality and characteristics")
def analyze_voice_quality(voice_id: str) -> TextContent:
    """Analyze voice quality."""
    try:
        # Get voice details
        voice = client.voices.get(voice_id=voice_id)
        
        # Get voice settings if available
        try:
            settings = client.voices.get_settings(voice_id=voice_id)
            settings_info = f"\nVoice Settings:\n{settings.model_dump_json(indent=2)}"
        except:
            settings_info = "\nVoice Settings: Not available"
        
        analysis = f"""Voice Quality Analysis for {voice.name} (ID: {voice_id})

Basic Information:
- Name: {voice.name}
- Category: {voice.category}
- Description: {voice.description or 'N/A'}
{settings_info}

Quality Indicators:
- Fine-tuning Status: {getattr(voice, 'fine_tuning_status', 'Not applicable')}
- Available: {'Yes' if voice else 'No'}
"""
        return TextContent(type="text", text=analysis)
    except Exception as e:
        make_error(f"Failed to analyze voice quality: {str(e)}")
        return TextContent(type="text", text="")


# ============================================================================
# WORKSPACE MANAGEMENT TOOLS
# ============================================================================

@mcp.tool(description="List all workspace secrets")
def list_workspace_secrets() -> TextContent:
    """List workspace secrets."""
    try:
        response = client.conversational_ai.secrets.list()
        
        secret_info = []
        secret_info.append(f"Workspace Secrets: {len(response.secrets)}")
        
        for secret in response.secrets:
            secret_info.append(f"Name: {secret.name}")
            secret_info.append(f"ID: {secret.secret_id}")
            secret_info.append(f"Created: {datetime.fromtimestamp(secret.created_at_unix_secs).strftime('%Y-%m-%d %H:%M:%S')}")
            secret_info.append("")
        
        return TextContent(type="text", text="\n".join(secret_info))
    except Exception as e:
        make_error(f"Failed to list workspace secrets: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Create a workspace secret")
def create_workspace_secret(name: str, value: str) -> TextContent:
    """Create workspace secret."""
    try:
        response = client.conversational_ai.secrets.create(
            name=name,
            value=value,
        )
        return TextContent(
            type="text",
            text=f"Workspace secret created: {response.name} (ID: {response.secret_id})"
        )
    except Exception as e:
        make_error(f"Failed to create workspace secret: {str(e)}")
        return TextContent(type="text", text="")


@mcp.tool(description="Delete a workspace secret")
def delete_workspace_secret(secret_id: str) -> TextContent:
    """Delete workspace secret."""
    try:
        client.conversational_ai.secrets.delete(secret_id)
        return TextContent(type="text", text=f"Workspace secret {secret_id} deleted successfully.")
    except Exception as e:
        make_error(f"Failed to delete workspace secret: {str(e)}")
        return TextContent(type="text", text="")
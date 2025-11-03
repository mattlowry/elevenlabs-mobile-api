![export](https://github.com/user-attachments/assets/ee379feb-348d-48e7-899c-134f7f7cd74f)

<div class="title-block" style="text-align: center;" align="center">

  [![Discord Community](https://img.shields.io/badge/discord-@elevenlabs-000000.svg?style=for-the-badge&logo=discord&labelColor=000)](https://discord.gg/elevenlabs)
  [![Twitter](https://img.shields.io/badge/Twitter-@elevenlabsio-000000.svg?style=for-the-badge&logo=twitter&labelColor=000)](https://x.com/ElevenLabsDevs)
  [![PyPI](https://img.shields.io/badge/PyPI-elevenlabs--mcp-000000.svg?style=for-the-badge&logo=pypi&labelColor=000)](https://pypi.org/project/elevenlabs-mcp)
  [![Tests](https://img.shields.io/badge/tests-passing-000000.svg?style=for-the-badge&logo=github&labelColor=000)](https://github.com/elevenlabs/elevenlabs-mcp-server/actions/workflows/test.yml)

</div>


<p align="center">
  Official ElevenLabs <a href="https://github.com/modelcontextprotocol">Model Context Protocol (MCP)</a> server with <strong>78 comprehensive tools</strong> for Text to Speech, voice cloning, conversational AI, audio processing, and advanced analytics. This enhanced SDK-based server allows MCP clients like <a href="https://www.anthropic.com/claude">Claude Desktop</a>, <a href="https://www.cursor.so">Cursor</a>, <a href="https://codeium.com/windsurf">Windsurf</a>, <a href="https://github.com/openai/openai-agents-python">OpenAI Agents</a> and others to generate speech, clone voices, create AI agents, analyze conversations, and much more.
</p>

## ✨ What's New in Enhanced v2.0

- **🚀 78 Tools** (up from 25) - Complete ElevenLabs API coverage
- **🤖 Conversational AI** - Create, manage, and analyze AI agents
- **📊 Analytics** - Conversation analytics and performance reports
- **🎯 Voice Design** - Advanced voice cloning and customization
- **📁 Batch Processing** - Process multiple files efficiently
- **⏱️ Timestamps** - TTS with character-level timing data
- **🔊 Audio Processing** - Enhanced sound effects and isolation
- **📋 Project Management** - Studio projects and workspace tools

<!--
mcp-name: io.github.elevenlabs/elevenlabs-mcp
-->

## Quickstart with Claude Desktop

1. Get your API key from [ElevenLabs](https://elevenlabs.io/app/settings/api-keys). There is a free tier with 10k credits per month.
2. Install `uv` (Python package manager), install with `curl -LsSf https://astral.sh/uv/install.sh | sh` or see the `uv` [repo](https://github.com/astral-sh/uv) for additional install methods.
3. Go to Claude > Settings > Developer > Edit Config > claude_desktop_config.json to include the following:

```
{
  "mcpServers": {
    "ElevenLabs": {
      "command": "uvx",
      "args": ["elevenlabs-mcp"],
      "env": {
        "ELEVENLABS_API_KEY": "your_api_key_here"
      }
    }
  }
}

```

If you're using Windows, you will have to enable "Developer Mode" in Claude Desktop to use the MCP server. Click "Help" in the hamburger menu at the top left and select "Enable Developer Mode".

## Quick Environment Setup

For local development and testing, you can use the provided environment files:

1. **Using .env file (recommended for local use)**:
   ```bash
   # The API key is already configured in .env
   # Just source the environment variables:
   source .env
   
   # Or run the quick setup script:
   python scripts/quick_setup.py
   ```

2. **Development testing**:
   ```bash
   # Run the conversational agent demo:
   python examples/conversational_agent_demo.py
   
   # Start the MCP server directly:
   python -m elevenlabs_mcp.server
   ```

## Other MCP clients

For other clients like Cursor and Windsurf, run:
1. `pip install elevenlabs-mcp`
2. `python -m elevenlabs_mcp --api-key={{PUT_YOUR_API_KEY_HERE}} --print` to get the configuration. Paste it into appropriate configuration directory specified by your MCP client.

That's it. Your MCP client can now interact with ElevenLabs through these tools:

## Example usage

⚠️ Warning: ElevenLabs credits are needed to use these tools.

Try asking Claude:

- "Create an AI agent that speaks like a film noir detective and can answer questions about classic movies"
- "Generate three voice variations for a wise, ancient dragon character, then I will choose my favorite voice to add to my voice library"
- "Convert this recording of my voice to sound like a medieval knight"
- "Create a soundscape of a thunderstorm in a dense jungle with animals reacting to the weather"
- "Turn this speech into text, identify different speakers, then convert it back using unique voices for each person"

## Optional features

### File Output Configuration

You can configure how the MCP server handles file outputs using these environment variables in your `claude_desktop_config.json`:

- **`ELEVENLABS_MCP_BASE_PATH`**: Specify the base path for file operations with relative paths (default: `~/Desktop`)
- **`ELEVENLABS_MCP_OUTPUT_MODE`**: Control how generated files are returned (default: `files`)

#### Output Modes

The `ELEVENLABS_MCP_OUTPUT_MODE` environment variable supports three modes:

1. **`files`** (default): Save files to disk and return file paths
   ```json
   "env": {
     "ELEVENLABS_API_KEY": "your-api-key",
     "ELEVENLABS_MCP_OUTPUT_MODE": "files"
   }
   ```

2. **`resources`**: Return files as MCP resources; binary data is base64-encoded, text is returned as UTF-8 text
   ```json
   "env": {
     "ELEVENLABS_API_KEY": "your-api-key",
     "ELEVENLABS_MCP_OUTPUT_MODE": "resources"
   }
   ```

3. **`both`**: Save files to disk AND return as MCP resources
   ```json
   "env": {
     "ELEVENLABS_API_KEY": "your-api-key",
     "ELEVENLABS_MCP_OUTPUT_MODE": "both"
   }
   ```

**Resource Mode Benefits:**
- Files are returned directly in the MCP response as base64-encoded data
- No disk I/O required - useful for containerized or serverless environments
- MCP clients can access file content immediately without file system access
- In `both` mode, resources can be fetched later using the `elevenlabs://filename` URI pattern

**Use Cases:**
- `files`: Traditional file-based workflows, local development
- `resources`: Cloud environments, MCP clients without file system access
- `both`: Maximum flexibility, caching, and resource sharing scenarios

### Data residency keys

You can specify the data residency region with the `ELEVENLABS_API_RESIDENCY` environment variable. Defaults to `"us"`.

**Note:** Data residency is an enterprise only feature. See [the docs](https://elevenlabs.io/docs/product-guides/administration/data-residency#overview) for more details.

## Contributing

If you want to contribute or run from source:

1. Clone the repository:

```bash
git clone https://github.com/elevenlabs/elevenlabs-mcp
cd elevenlabs-mcp
```

2. Create a virtual environment and install dependencies [using uv](https://github.com/astral-sh/uv):

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

3. Copy `.env.example` to `.env` and add your ElevenLabs API key:

```bash
cp .env.example .env
# Edit .env and add your API key
```

4. Run the tests to make sure everything is working:

```bash
./scripts/test.sh
# Or with options
./scripts/test.sh --verbose --fail-fast
```

5. Install the server in Claude Desktop: `mcp install elevenlabs_mcp/server.py`

6. Debug and test locally with MCP Inspector: `mcp dev elevenlabs_mcp/server.py`

## Troubleshooting

Logs when running with Claude Desktop can be found at:

- **Windows**: `%APPDATA%\Claude\logs\mcp-server-elevenlabs.log`
- **macOS**: `~/Library/Logs/Claude/mcp-server-elevenlabs.log`

### Timeouts when using certain tools

Certain ElevenLabs API operations, like voice design and audio isolation, can take a long time to resolve. When using the MCP inspector in dev mode, you might get timeout errors despite the tool completing its intended task.

This shouldn't occur when using a client like Claude.

### MCP ElevenLabs: spawn uvx ENOENT

If you encounter the error "MCP ElevenLabs: spawn uvx ENOENT", confirm its absolute path by running this command in your terminal:

```bash
which uvx
```

Once you obtain the absolute path (e.g., `/usr/local/bin/uvx`), update your configuration to use that path (e.g., `"command": "/usr/local/bin/uvx"`). This ensures that the correct executable is referenced.



## 🛠️ Complete Tool Suite (78 Tools)

This enhanced MCP server provides **78 comprehensive tools** across all ElevenLabs capabilities:

### 🤖 Conversational AI (20+ tools)
- **Agent Management**: Create, update, delete, duplicate, and analyze agents
- **Templates**: 9 pre-configured agent types (customer service, sales, support, etc.)
- **Knowledge Base**: Document integration (PDF, DOCX, TXT, HTML)
- **Phone Integration**: Twilio and SIP trunk support
- **Analytics**: Performance metrics, conversation reports, LLM usage tracking

### 🎙️ Text-to-Speech & Voice (12+ tools) 
- **Voice Synthesis**: High-quality TTS with 29+ language support
- **Voice Cloning**: Instant and advanced voice cloning with labels
- **Voice Design**: Generate voices from text descriptions
- **Audio Processing**: Isolation, enhancement, sound effects
- **Batch Processing**: Multiple file processing capabilities

### 📊 Analytics & Management (15+ tools)
- **History Management**: Generation history, file management
- **Studio Projects**: Project organization and management
- **Conversation Analytics**: Detailed performance reports
- **User Management**: Subscription info, workspace secrets
- **Pronunciation**: Custom dictionaries and rule management

### 🔧 Advanced Features (30+ tools)
- **Audio Processing**: Speech-to-text, voice conversion, alignment
- **Dubbing**: Video/audio dubbing projects
- **Audio Native**: Dynamic audio generation
- **Webhooks**: Event management and automation
- **Streaming**: Real-time TTS and conversation simulation

---

## 🤖 Conversational AI Agent Features

This MCP server provides comprehensive tools for building and managing **conversational AI agents** with ElevenLabs' advanced voice technology:

### Agent Creation & Management

- **🛠️ Template-Based Agent Creation**: Create agents from pre-configured templates for different use cases:
  - Customer Service representatives
  - Sales assistants  
  - Technical support specialists
  - Personal assistants
  - Creative writers
  - Educators
  - Therapeutic conversation partners
  - Interviewers
  - Fitness trainers

- **⚙️ Advanced Agent Configuration**: Fine-tune every aspect of your conversational agents:
  - Custom system prompts and personalities
  - Voice selection and speech parameters (stability, similarity boost, style)
  - Language settings and LLM integration
  - Conversation timing and timeout controls
  - ASR quality and streaming optimization

- **📊 Agent Lifecycle Management**: Complete agent lifecycle operations:
  - Create, update, delete, and duplicate agents
  - Copy configurations between agents
  - Batch management capabilities
  - Performance tracking and analytics

### Knowledge Base Integration

- **📚 Smart Knowledge Integration**: Enhance agents with domain-specific knowledge:
  - Upload documents (PDF, DOCX, TXT, HTML)
  - Add knowledge from URLs
  - Integrate custom text content
  - Automatic knowledge base organization

### Phone Integration & Communication

- **📞 Voice Calling Integration**: Connect agents to phone systems:
  - Twilio integration for outbound calls
  - SIP trunk support
  - Phone number management
  - Call monitoring and control

### Conversation Analytics & Insights

- **📈 Performance Analytics**: Deep insights into agent performance:
  - Conversation success rates and metrics
  - Average conversation duration and message counts
  - Response quality indicators
  - Status distribution analysis

- **📋 Comprehensive Reporting**: Generate detailed analytics reports:
  - JSON, CSV, and summary formats
  - Multi-agent comparison capabilities
  - Customizable time periods
  - Performance score calculation

### Conversation Management

- **💬 Real-time Conversation Monitoring**: Access and analyze conversations:
  - Complete transcript retrieval
  - Speaker identification and diarization
  - Conversation metadata and timing
  - Call success/failure analysis

- **🔍 Conversation Search & Analysis**: Find and analyze specific conversations:
  - Filter by date ranges and agent IDs
  - Pagination for large conversation sets
  - Transcript parsing with speaker labels
  - Conversation flow analysis

### Advanced Voice & Audio Features

- **🎙️ High-Quality Voice Synthesis**: Professional-grade text-to-speech:
  - Multi-language support (29+ languages)
  - Voice cloning and customization
  - Real-time streaming capabilities
  - Emotion and prosody controls

- **🎧 Audio Processing**: Complete audio workflow support:
  - Speech-to-text with speaker diarization
  - Voice-to-voice conversion
  - Audio isolation and enhancement
  - Sound effects and music generation

### Example Conversational Agent Use Cases

1. **Customer Support Agent**: 
   ```
   Create an AI agent that speaks like a friendly customer service representative 
   and can answer questions about my company's products and policies
   ```

2. **Sales Assistant**:
   ```
   Generate three voice variations for a professional sales agent, then create 
   an agent that can guide customers through product selection
   ```

3. **Educational Tutor**:
   ```
   Build a patient educational agent that can explain complex topics in simple terms
   and adapt to the learner's level of understanding
   ```

4. **Healthcare Companion**:
   ```
   Create a therapeutic conversation partner that provides emotional support 
   and helps users process their feelings
   ```

5. **Technical Support Specialist**:
   ```
   Build a technical agent that can diagnose issues systematically and provide 
   step-by-step troubleshooting instructions
   ```

### Quick Agent Creation Examples

**Create a Customer Service Agent:**
```python
# Using the template system
create_agent_from_template(
    name="Customer Service Bot",
    template_type="customer_service",
    voice_id="custom_voice_id",
    language="en"
)
```

**Create a Custom Agent:**
```python
# Full configuration
create_agent(
    name="My Custom Agent",
    first_message="Hello! How can I assist you today?",
    system_prompt="You are a helpful and knowledgeable assistant...",
    voice_id="voice_id",
    language="en",
    llm="gemini-2.0-flash-001"
)
```

**Add Knowledge Base:**
```python
# Add company documentation
add_knowledge_base_to_agent(
    agent_id="agent_id",
    knowledge_base_name="Product Knowledge",
    url="https://company.com/docs"
)
```

### Performance Monitoring

**Analyze Agent Performance:**
```python
analyze_agent_performance(
    agent_id="agent_id",
    days_back=30,
    min_conversations=10
)
```

**Generate Analytics Report:**
```python
generate_conversation_analytics_report(
    agent_ids="agent1,agent2,agent3",
    days_back=30,
    report_format="summary"
)
```

---

## 🚀 Getting Started with Conversational Agents

1. **Choose an Agent Type**: Select from templates or create custom agents
2. **Configure Voice & Personality**: Set up voice parameters and system prompts
3. **Add Knowledge**: Integrate relevant information sources
4. **Test & Optimize**: Use analytics to improve performance
5. **Deploy & Monitor**: Launch agents and track conversation quality

The ElevenLabs MCP server provides everything you need to build sophisticated conversational AI applications with enterprise-grade voice technology!
# ElevenLabs MCP Server Configuration Examples

## Environment Variables

### Required
```bash
export ELEVENLABS_API_KEY="sk_ece916657aa72d5b07ef1609c068cea8aec243065fa73fae"
```

### Optional Configuration
```bash
# Base path for file operations (default: ~/Desktop)
export ELEVENLABS_MCP_BASE_PATH="/path/to/your/output/directory"

# Output mode: 'files', 'resources', or 'both' (default: 'files')
export ELEVENLABS_MCP_OUTPUT_MODE="files"

# Data residency region: 'us', 'eu-residency', 'in-residency', 'global' (default: 'us')
export ELEVENLABS_API_RESIDENCY="us"

# Default voice ID to use when none specified
export ELEVENLABS_DEFAULT_VOICE_ID="cgSgspJ2msm6clMCkdW9"
```

## MCP Client Configuration

### Claude Desktop Configuration
Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ElevenLabs": {
      "command": "uvx",
      "args": ["elevenlabs-mcp"],
      "env": {
        "ELEVENLABS_API_KEY": "sk_ece916657aa72d5b07ef1609c068cea8aec243065fa73fae",
        "ELEVENLABS_MCP_BASE_PATH": "~/Desktop",
        "ELEVENLABS_MCP_OUTPUT_MODE": "files"
      }
    }
  }
}
```

### Alternative (local installation):
```json
{
  "mcpServers": {
    "ElevenLabs": {
      "command": "python",
      "args": ["-m", "elevenlabs_mcp.server"],
      "env": {
        "ELEVENLABS_API_KEY": "sk_ece916657aa72d5b07ef1609c068cea8aec243065fa73fae",
        "ELEVENLABS_MCP_BASE_PATH": "~/Desktop"
      }
    }
  }
}
```

## Output Modes Explained

### Files Mode (default)
- Saves generated files to disk
- Returns file paths as text
- Good for: Local development, file management

### Resources Mode  
- Returns files as base64-encoded MCP resources
- No disk I/O required
- Good for: Cloud environments, containerized deployments

### Both Mode
- Saves files to disk AND returns as resources
- Maximum flexibility
- Good for: Development and production workflows

## Conversational Agent Setup Examples

### 1. Customer Service Agent
```python
# Create via template
create_agent_from_template(
    name="Customer Support Bot",
    template_type="customer_service", 
    voice_id="professional_voice_id",
    language="en"
)

# Add knowledge base
add_knowledge_base_to_agent(
    agent_id="agent_id",
    knowledge_base_name="Product FAQ",
    url="https://company.com/faq"
)
```

### 2. Sales Assistant
```python
# Create with custom configuration
create_agent(
    name="Sales Assistant",
    first_message="Hello! I'd love to help you find the perfect product. What are you looking for today?",
    system_prompt="You are a consultative sales assistant. Focus on understanding customer needs and providing value-driven recommendations.",
    voice_id="friendly_voice_id",
    language="en",
    temperature=0.6,
    stability=0.7,
    similarity_boost=0.8
)
```

### 3. Educational Tutor
```python
# Template-based creation
create_agent_from_template(
    name="Math Tutor",
    template_type="educator",
    custom_instructions="You are a patient math tutor who explains concepts step-by-step and adapts to the student's level.",
    knowledge_base_source="Math curriculum and practice problems"
)
```

## Performance Monitoring

### Individual Agent Analysis
```python
analyze_agent_performance(
    agent_id="your_agent_id",
    days_back=30,
    min_conversations=10
)
```

### Multi-Agent Analytics Report
```python
generate_conversation_analytics_report(
    agent_ids="agent1,agent2,agent3",
    days_back=30,
    report_format="summary",
    output_directory="/path/to/reports"
)
```

## Phone Integration Setup

### Prerequisites
1. Set up phone numbers in ElevenLabs dashboard
2. Configure Twilio or SIP trunk integration
3. Assign phone numbers to agents

### Usage
```python
# List available phone numbers
list_phone_numbers()

# Make outbound call
make_outbound_call(
    agent_id="agent_id",
    agent_phone_number_id="phone_number_id", 
    to_number="+1234567890"
)
```

## Error Handling Tips

### Common Issues and Solutions

1. **API Key Issues**
   - Verify ELEVENLABS_API_KEY is set correctly
   - Check API key has required permissions

2. **File Path Errors**
   - Use absolute paths when ELEVENLABS_MCP_BASE_PATH not set
   - Ensure output directory is writable

3. **Voice Not Found**
   - Use search_voices() to find available voices
   - Verify voice_id is correct and accessible

4. **Agent Creation Fails**
   - Check LLM model availability
   - Verify voice_id is valid
   - Ensure API credits are available

## Best Practices

### Agent Design
- Start with templates for common use cases
- Use descriptive agent names for easy management
- Set appropriate timeout values for your use case
- Test agents with various conversation scenarios

### Performance Monitoring
- Regular performance analysis (weekly/monthly)
- Track conversation success rates
- Monitor average conversation duration
- Analyze user feedback patterns

### Knowledge Base Management
- Keep knowledge sources up to date
- Use relevant, high-quality content
- Test knowledge retrieval regularly
- Organize knowledge by topic/category

### Voice Configuration
- Match voice personality to agent role
- Adjust stability for consistency vs. variation
- Use similarity boost for voice authenticity
- Test with different audio formats

## Troubleshooting Commands

### Check Agent Status
```python
manage_agent_lifecycle(action="list")
get_agent(agent_id="agent_id")
```

### Verify Phone Setup  
```python
list_phone_numbers()
```

### Test Voice Configuration
```python
search_voices(search="professional")
list_models()
```

### Debug File Operations
```python
# Check output directory and permissions
import os
print("Output directory:", os.getenv("ELEVENLABS_MCP_BASE_PATH", "~/Desktop"))
print("Writable:", os.access(os.path.expanduser("~/Desktop"), os.W_OK))
```

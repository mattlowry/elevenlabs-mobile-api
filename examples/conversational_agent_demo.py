#!/usr/bin/env python3
"""
ElevenLabs Conversational Agent Demo

This script demonstrates the key conversational agent features of the ElevenLabs MCP server.
Run this to see examples of how to create and manage conversational AI agents.

Prerequisites:
1. Set your ELEVENLABS_API_KEY environment variable (sk_ece916657aa72d5b07ef1609c068cea8aec243065fa73fae)
2. Install the required dependencies: pip install elevenlabs python-dotenv
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the MCP server
sys.path.insert(0, str(Path(__file__).parent.parent))

from elevenlabs_mcp.server import (
    create_agent_from_template,
    create_agent,
    add_knowledge_base_to_agent,
    analyze_agent_performance,
    generate_conversation_analytics_report,
    manage_agent_lifecycle,
    update_agent,
    list_agents,
    make_outbound_call,
    list_phone_numbers,
)


def demo_agent_templates():
    """Demonstrate creating agents from templates."""
    print("🤖 Creating Agent from Template")
    print("=" * 50)
    
    try:
        # Create a customer service agent
        result = create_agent_from_template(
            name="Demo Customer Service Agent",
            template_type="customer_service",
            language="en"
        )
        print("✅ Customer Service Agent Created:")
        print(result.text)
        print()
        
        # Create a sales assistant
        result = create_agent_from_template(
            name="Demo Sales Assistant", 
            template_type="sales_assistant",
            language="en"
        )
        print("✅ Sales Assistant Created:")
        print(result.text)
        print()
        
    except Exception as e:
        print(f"❌ Template Demo Error: {e}")


def demo_custom_agent():
    """Demonstrate creating a custom agent with full configuration."""
    print("🔧 Creating Custom Agent")
    print("=" * 50)
    
    try:
        result = create_agent(
            name="Demo Creative Assistant",
            first_message="Hello! I'm your creative writing companion. What story would you like to work on today?",
            system_prompt="""You are a creative writing assistant specializing in:
            - Story development and plot creation
            - Character development and dialogue
            - Writing techniques and style guidance
            - Genre-specific advice (fantasy, sci-fi, romance, etc.)
            
            Be encouraging, imaginative, and provide specific, actionable feedback.""",
            language="en",
            llm="gemini-2.0-flash-001",
            temperature=0.8,  # Higher creativity
            stability=0.6,
            similarity_boost=0.9,
            record_voice=True,
            retention_days=365
        )
        print("✅ Custom Creative Agent Created:")
        print(result.text)
        print()
        
    except Exception as e:
        print(f"❌ Custom Agent Demo Error: {e}")


def demo_agent_management():
    """Demonstrate agent lifecycle management."""
    print("⚙️ Agent Lifecycle Management")
    print("=" * 50)
    
    try:
        # List all agents
        result = manage_agent_lifecycle(action="list")
        print("📋 Current Agents:")
        print(result.text)
        print()
        
    except Exception as e:
        print(f"❌ Agent Management Demo Error: {e}")


def demo_analytics():
    """Demonstrate conversation analytics."""
    print("📊 Conversation Analytics Demo")
    print("=" * 50)
    
    try:
        # Note: This would require existing agent with conversation data
        # For demo purposes, showing the structure
        print("Analytics Features Available:")
        print("• analyze_agent_performance() - Individual agent metrics")
        print("• generate_conversation_analytics_report() - Comprehensive reports")
        print()
        print("To use analytics, you need:")
        print("1. An agent with conversation history")
        print("2. Call analyze_agent_performance(agent_id='your_agent_id')")
        print("3. Call generate_conversation_analytics_report(agent_ids='agent1,agent2')")
        print()
        
    except Exception as e:
        print(f"❌ Analytics Demo Error: {e}")


def demo_knowledge_base():
    """Demonstrate knowledge base integration."""
    print("📚 Knowledge Base Integration Demo")
    print("=" * 50)
    
    try:
        # Demo knowledge base features
        print("Knowledge Base Features:")
        print("• add_knowledge_base_to_agent() - Add documents, URLs, or text")
        print("• Support for PDF, DOCX, TXT, HTML formats")
        print("• URL-based knowledge integration")
        print("• Custom text content addition")
        print()
        print("Example usage:")
        print("add_knowledge_base_to_agent(")
        print("    agent_id='your_agent_id',")
        print("    knowledge_base_name='Company Handbook',")
        print("    url='https://company.com/handbook'")
        print(")")
        print()
        
    except Exception as e:
        print(f"❌ Knowledge Base Demo Error: {e}")


def demo_phone_integration():
    """Demonstrate phone integration features."""
    print("📞 Phone Integration Demo")
    print("=" * 50)
    
    try:
        # List phone numbers (would show actual phone numbers if configured)
        result = list_phone_numbers()
        print("📱 Available Phone Numbers:")
        print(result.text)
        print()
        print("Phone Integration Features:")
        print("• make_outbound_call() - Initiate calls through Twilio/SIP")
        print("• Automatic provider detection")
        print("• Call monitoring and control")
        print()
        
    except Exception as e:
        print(f"❌ Phone Integration Demo Error: {e}")


def main():
    """Run all demonstrations."""
    print("🚀 ElevenLabs Conversational Agent MCP Server Demo")
    print("=" * 60)
    print()
    
    # Check if API key is set
    if not os.getenv("ELEVENLABS_API_KEY"):
        print("⚠️  Warning: ELEVENLABS_API_KEY environment variable not set.")
        print("   Please set your API key to run the full demo:")
        print("   export ELEVENLABS_API_KEY='your_api_key_here'")
        print()
    
    print("This demo shows the conversational agent capabilities:")
    print("• Agent creation from templates")
    print("• Custom agent configuration") 
    print("• Agent lifecycle management")
    print("• Conversation analytics")
    print("• Knowledge base integration")
    print("• Phone system integration")
    print()
    
    # Run demonstrations
    try:
        demo_agent_templates()
        demo_custom_agent()
        demo_agent_management()
        demo_analytics()
        demo_knowledge_base()
        demo_phone_integration()
        
        print("🎉 Demo completed! Check the ElevenLabs MCP server documentation")
        print("   for detailed usage instructions and all available tools.")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("Make sure your ELEVENLABS_API_KEY is set correctly.")


if __name__ == "__main__":
    main()

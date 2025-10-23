#!/usr/bin/env python3
"""
# 🧠 Memory Agent

A demonstration of using Strands Agents' memory capabilities to store and retrieve information.

## What This Example Shows

This example demonstrates:
- Creating an agent with memory capabilities
- Storing information for later retrieval
- Retrieving relevant memories based on context
- Using memory to create personalized responses

## Usage Examples

Basic usage:
```
uv run memory_agent.py
```

## Memory Operations

1. **Store Information**:
   - "Remember that I like hiking"
   - "Note that I have a dog named Max"
   - "I want you to know I prefer window seats"

2. **Retrieve Information**:
   - "What do you know about me?"
   - "What are my hobbies?"
   - "Do I have any pets?"

3. **List All Memories**:
   - "Show me everything you remember"
   - "What memories do you have stored?"
"""

import os
import logging
from dotenv import load_dotenv

from strands import Agent
from strands.models import BedrockModel
from strands_tools import mem0_memory, use_agent
from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider

logger = logging.getLogger(__name__)

# Load environment variables from .env file if it exists
load_dotenv()

USER_ID = os.getenv('USER_ID', 'J')
AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')

# System prompt for the memory agent
MEMORY_SYSTEM_PROMPT = f"""You are a personal assistant that maintains context by remembering user details.

Capabilities:
- Store new information using mem0_memory tool (action="store")
- Retrieve relevant memories (action="retrieve")
- List all memories (action="list")
- Provide personalized responses

Key Rules:
- Always include user_id={USER_ID} in tool calls
- Be conversational and natural in responses
- Format output clearly
- Acknowledge stored information
- Only share relevant information
- Politely indicate when information is unavailable
"""

# Setup Bedrock
bedrock_model = BedrockModel(
    model_id='us.amazon.nova-pro-v1:0',
    temperature=0.1,
)

# Set USE_AGENTCORE_MEMORY=True to use AgentCore Memory
# USE_AGENTCORE_MEMORY = os.getenv('USE_AGENTCORE_MEMORY', '')
USE_AGENTCORE_MEMORY = None  # Disable AgentCore Memory for now
if USE_AGENTCORE_MEMORY:
    provider = AgentCoreMemoryToolProvider(
        memory_id="memory-123abc4567",  # Required
        actor_id=USER_ID,               # Required
        session_id="session-789",       # Required
        namespace="default",            # Required
        region=AWS_DEFAULT_REGION       # Optional, defaults to us-west-2
    )
    memory_tool = provider.tools
else:
    memory_tool = mem0_memory

# Create an agent with memory capabilities
memory_agent = Agent(
    model=bedrock_model,
    system_prompt=MEMORY_SYSTEM_PROMPT,
    tools=[memory_tool, use_agent]
)

# Setup
def initialize_demo_memories(memory_agent) -> None:
    init_memories = (
        f"My name is {USER_ID}. "
        "I like to travel and stay in Airbnbs rather than hotels. "
        "I enjoy hiking and outdoor photography as hobbies. "
        "I have a dog named Max. "
        "My favorite cuisine is Italian food."
    )

    if USE_AGENTCORE_MEMORY:
        # Default: AgentCore Memory
        memory_agent.tool.agent_core_memory(
            action = "record",
            content = init_memories
        )
    else:
        memory_agent.tool.mem0_memory(
            action = "store",
            content = init_memories,
            user_id = USER_ID
        )

def demo():
   initialize_demo_memories(memory_agent)
   memory_agent("I work in marketing.", invocation_state={"user_id": USER_ID})
   memory_agent("I am 32 years old.", invocation_state={"user_id": USER_ID})
   memory_agent("What do you remember about me?", invocation_state={"user_id": USER_ID})
   print()

# Example usage
if __name__ == "__main__":
    print("\n🧠 Memory Agent 🧠\n")
    print("This example demonstrates using Strands Agents' memory capabilities")
    print("to store and retrieve information.")
    print("\nOptions:")
    print("  'demo' - Run demo and exit")
    print("  'exit' - Exit the program")
    print("\nOr try these examples:")
    print("  - I am 45 years old")
    print("  - What is my age?")
    print("  - Do I have any pets?")
    print("  - What do you know about me?")

    # Interactive loop
    while True:
        try:
            user_input = input("\n> ")

            if user_input.lower() == "exit":
                print("\nGoodbye! 👋")
                break
            elif user_input.lower() == "demo":
                demo()
                break

            # Call the memory agent
            memory_agent(user_input, invocation_state={"user_id": USER_ID})

        except KeyboardInterrupt:
            print("\n\nExecution interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            print("Please try a different request.")

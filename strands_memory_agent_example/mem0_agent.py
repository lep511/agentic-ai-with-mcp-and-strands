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
python mem0_agent.py
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
from strands import Agent
from strands.models import BedrockModel
from strands_tools import mem0_memory, use_llm

USER_ID = os.getenv('USER_ID', 'Alex')

SYSTEM_PROMPT = """
You remember user preferences.
"""

# Setup
def initialize_demo_memories(memory_agent) -> None:
    init_memories = f"My name is {USER_ID}. I like to travel and stay in Airbnbs rather than hotels. I am planning a trip to Japan next spring. I enjoy hiking and outdoor photography as hobbies. I have a dog named Max. My favorite cuisine is Italian food."
    memory_agent.tool.mem0_memory(
        action = "store",
        content = init_memories,
        user_id = USER_ID
    )

model = BedrockModel(model_id='anthropic.claude-3-haiku-20240307-v1:0')

memory_agent = Agent(
   model=model,
   system_prompt=SYSTEM_PROMPT,
   tools=[mem0_memory, use_llm],
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

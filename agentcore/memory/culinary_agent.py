import time
import logging
from datetime import datetime
import os
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.constants import StrategyType
from botocore.exceptions import ClientError
from strands import Agent
from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("culinary-memory")

def main():
    region = os.getenv('AWS_REGION', 'us-west-2')
    client = MemoryClient(region_name=region)
    memory_name = "CulinaryAssistant"
    
    actor_id = f"user-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    session_id = f"foodie-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    namespace = f"user/{actor_id}/preferences"
    memory_id = None

    previous_messages = [
        ("Hi, I'm John", "USER"),
        ("Hi John, how can I help you with food recommendations today?", "ASSISTANT"),
        ("I'm looking for some vegetarian dishes to try this weekend.", "USER"),
        ("That sounds great! I'd be happy to help with vegetarian recommendations. Do you have any specific ingredients or cuisine types you prefer?", "ASSISTANT"),
        ("Yes, I really like tofu and fresh vegetables in my dishes", "USER"),
        ("Perfect! Tofu and fresh vegetables make for excellent vegetarian meals. I can suggest some stir-fries, Buddha bowls, or tofu curries. Do you have any other preferences?", "ASSISTANT"),
        ("I also really enjoy Italian cuisine. I love pasta dishes and would like them to be vegetarian-friendly.", "USER"),
        ("Excellent! Italian cuisine has wonderful vegetarian options. I can recommend pasta primavera, mushroom risotto, eggplant parmesan, or penne arrabbiata. The combination of Italian flavors with vegetarian ingredients creates delicious meals!", "ASSISTANT"),
        ("I spent 2 hours looking through cookbooks but couldn't find inspiring vegetarian Italian recipes", "USER"),
        ("I'm sorry you had trouble finding inspiring recipes! Let me help you with some creative vegetarian Italian dishes. How about stuffed bell peppers with Italian herbs and rice, spinach and ricotta cannelloni, or a Mediterranean vegetable lasagna?", "ASSISTANT"),
        ("Hey, I appreciate food assistants with good taste", "USER"),
        ("Ha! I definitely try to bring good taste to the table! Speaking of which, shall we explore some more vegetarian Italian recipes that might inspire you?", "ASSISTANT")
    ]

    try:
        print("Creating Long-Term Memory...")
        
        # Create memory with user preference strategy
        memory = client.create_memory_and_wait(
            name=memory_name,
            description="Culinary Assistant Agent with long term memory",
            strategies=[{
                        StrategyType.USER_PREFERENCE.value: {
                            "name": "UserPreferences",
                            "description": "Captures user preferences",
                            "namespaces": ["user/{actorId}/preferences"]
                        }
                    }],
            event_expiry_days=7,
            max_wait=300,
            poll_interval=10
        )
        
        memory_id = memory['id']
        print(f"Memory created successfully with ID: {memory_id}")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ValidationException' and "already exists" in str(e):
            # If memory already exists, retrieve its ID
            memories = client.list_memories()
            memory_id = next((m['id'] for m in memories if m['id'].startswith(memory_name)), None)
            logger.info(f"Memory already exists. Using existing memory ID: {memory_id}")
    except Exception as e:
        # Handle any errors during memory creation
        logger.info(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return
    
    if not memory_id:
        logger.error("Failed to create or retrieve memory ID")
        return
    
    print("\nHydrating short term memory with previous conversations...")
    
    # Save the conversation history to short-term memory
    client.create_event(
        memory_id=memory_id,
        actor_id=actor_id,
        session_id=session_id,
        messages=previous_messages,
    )
    print("✓ Conversation saved in short term memory")
    
    # Create memory tool provider
    memory_tool = AgentCoreMemoryToolProvider(
        memory_id=memory_id,
        actor_id=actor_id,
        session_id=session_id,
        namespace=namespace
    )
    
    # Create culinary agent
    culinary_agent = Agent(
        tools=[memory_tool],
        model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        system_prompt="""You are the Culinary Assistant, a sophisticated restaurant recommendation assistant.

PURPOSE:
- Help users discover restaurants based on their preferences
- Remember user preferences throughout the conversation
- Provide personalized dining recommendations

You have access to a Memory tool that enables you to:
- Store user preferences (dietary restrictions, favorite cuisines, budget preferences, etc.)
- Retrieve previously stored information to personalize recommendations
"""
    )
    
    print("✅ Culinary agent created with memory capabilities")
    
    # Interactive loop for user queries
    while True:
        try:
            query = input("\nEnter your culinary query (or 'quit' to exit): ")
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            # Display memory summary
            print("\n🍽️ Food Preferences Summary:")
            print("=" * 40)
            
            try:
                time.sleep(30)
                food_preferences = client.retrieve_memories(
                    memory_id=memory_id,
                    namespace=namespace,
                    query="food preferences",
                    top_k=3
                )
                
                if food_preferences:
                    for i, record in enumerate(food_preferences, 1):
                        content = record.get('content', {})
                        if isinstance(content, dict):
                            text = content.get('text', '')[:100] + "..."
                            print(f"  {i}. {text}")
                else:
                    print("  No preferences stored yet")
                    
            except Exception as e:
                print(f"Error retrieving preferences: {e}")
            
            print("=" * 40)
            
            response = culinary_agent(query)
            print(f"\nCulinary Assistant: {response}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()


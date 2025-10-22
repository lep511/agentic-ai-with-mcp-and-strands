import logging
import json
import os
from typing import Dict
from datetime import datetime
from botocore.exceptions import ClientError
from strands import Agent, tool
from strands.hooks import AfterInvocationEvent, HookProvider, HookRegistry, MessageAddedEvent
from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException
from ddgs import DDGS
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.constants import StrategyType

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("customer-support")

@tool
def web_search(query: str, max_results: int = 3) -> str:
    """Search the web for product information, troubleshooting guides, or support articles.
    
    Args:
        query: Search query for product info or troubleshooting
        max_results: Maximum number of results to return
    
    Returns:
        Search results with titles and snippets
    """
    try:
        results = DDGS().text(query, region="us-en", max_results=max_results)
        if not results:
            return "No search results found."
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append(f"{i}. {result.get('title', 'No title')}\n   {result.get('body', 'No description')}")
        
        return "\n".join(formatted_results)
    except RatelimitException:
        return "Rate limit reached: Please try again after a short delay."
    except DuckDuckGoSearchException as d:
        return f"Search Error: {d}"
    except Exception as e:
        return f"Search error: {str(e)}"

logger.info("✅ Web search tool ready")

@tool
def check_order_status(order_number: str) -> str:
    """Check the status of a customer order.
    
    Args:
        order_number: The order number to check
    
    Returns:
        Order status information
    """
    # Simulate order lookup
    mock_orders = {
        "123456": "iPhone 15 Pro - Delivered on June 5, 2025",
        "654321": "Sennheiser Headphones - Delivered on June 25, 2025, 1-year warranty active",
        "789012": "Samsung Galaxy S23 - In transit, expected delivery on July 1, 2025",
    }
    
    return mock_orders.get(order_number, f"Order {order_number} not found. Please verify the order number.")

logger.info("✅ Check Order Status tool ready")

# Helper function to get namespaces from memory strategies list
def get_namespaces(mem_client: MemoryClient, memory_id: str) -> Dict:
    """Get namespace mapping for memory strategies."""
    strategies = mem_client.get_memory_strategies(memory_id)
    return {i["type"]: i["namespaces"][0] for i in strategies}

class CustomerSupportMemoryHooks(HookProvider):
    """Memory hooks for customer support agent"""
    
    def __init__(self, memory_id: str, client: MemoryClient, actor_id: str, session_id: str):
        self.memory_id = memory_id
        self.client = client
        self.actor_id = actor_id
        self.session_id = session_id
        self.namespaces = get_namespaces(self.client, self.memory_id)

    
    def retrieve_customer_context(self, event: MessageAddedEvent):
        """Retrieve customer context before processing support query"""
        messages = event.agent.messages
        if messages[-1]["role"] == "user" and "toolResult" not in messages[-1]["content"][0]:
            user_query = messages[-1]["content"][0]["text"]
            
            try:
                # Retrieve customer context from all namespaces
                all_context = []
                
                for context_type, namespace in self.namespaces.items():
                    memories = self.client.retrieve_memories(
                        memory_id=self.memory_id,
                        namespace=namespace.format(actorId=self.actor_id),
                        query=user_query,
                        top_k=3
                    )
                    
                    for memory in memories:
                        if isinstance(memory, dict):
                            content = memory.get('content', {})
                            if isinstance(content, dict):
                                text = content.get('text', '').strip()
                                if text:
                                    all_context.append(f"[{context_type.upper()}] {text}")
                
                # Inject customer context into the query
                if all_context:
                    context_text = "\n".join(all_context)
                    original_text = messages[-1]["content"][0]["text"]
                    messages[-1]["content"][0]["text"] = (
                        f"Customer Context:\n{context_text}\n\n{original_text}"
                    )
                    logger.info(f"Retrieved {len(all_context)} customer context items")
                    
            except Exception as e:
                logger.error(f"Failed to retrieve customer context: {e}")
    
    def save_support_interaction(self, event: AfterInvocationEvent):
        """Save support interaction after agent response"""
        try:
            messages = event.agent.messages
            if len(messages) >= 2 and messages[-1]["role"] == "assistant":
                # Get last customer query and agent response
                customer_query = None
                agent_response = None
                
                for msg in reversed(messages):
                    if msg["role"] == "assistant" and not agent_response:
                        agent_response = msg["content"][0]["text"]
                    elif msg["role"] == "user" and not customer_query and "toolResult" not in msg["content"][0]:
                        customer_query = msg["content"][0]["text"]
                        break
                
                if customer_query and agent_response:
                    # Save the support interaction
                    self.client.create_event(
                        memory_id=self.memory_id,
                        actor_id=self.actor_id,
                        session_id=self.session_id,
                        messages=[(customer_query, "USER"), (agent_response, "ASSISTANT")]
                    )
                    logger.info("Saved support interaction to memory")
                    
        except Exception as e:
            logger.error(f"Failed to save support interaction: {e}")

    def register_hooks(self, registry: HookRegistry) -> None:
        """Register customer support memory hooks"""
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_support_interaction)
        logger.info("Customer support memory hooks registered")

def main():
    region = os.environ.get('AWS_REGION', 'us-west-2')
    CUSTOMER_ID = "customer_001"
    SESSION_ID = f"support_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Initialize Memory Client
    client = MemoryClient(region_name=region)
    memory_name = "CustomerSupportMemory"

    # Initialize memory_id to prevent UnboundLocalError
    memory_id = None
    
    # Define memory strategies for customer support
    strategies = [
        {
            StrategyType.USER_PREFERENCE.value: {
                "name": "CustomerPreferences",
                "description": "Captures customer preferences and behavior",
                "namespaces": ["support/customer/{actorId}/preferences"]
            }
        },
        {
            StrategyType.SEMANTIC.value: {
                "name": "CustomerSupportSemantic",
                "description": "Stores facts from conversations",
                "namespaces": ["support/customer/{actorId}/semantic"],
            }
        }
    ]

    # Create memory resource
    try:
        memory = client.create_memory_and_wait(
            name=memory_name,
            strategies=strategies,         # Define the memory strategies
            description="Memory for customer support agent",
            event_expiry_days=90,          # Memories expire after 90 days
        )
        memory_id = memory['id']
        logger.info(f"✅ Created memory: {memory_id}")
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

    strategies = client.get_memory_strategies(memory_id)
    print(json.dumps(strategies, indent=2, default=str))

    # Create memory hooks for customer support
    support_hooks = CustomerSupportMemoryHooks(
        memory_id=memory_id,
        client=client,
        actor_id=CUSTOMER_ID,
        session_id=SESSION_ID
    )

    # Create customer support agent
    support_agent = Agent(
        hooks=[support_hooks],
        model="anthropic.claude-3-5-sonnet-20241022-v2:0",
        tools=[web_search, check_order_status],
        system_prompt="""You are a helpful customer support agent with access to customer history and order information. 
        
        Your role:
        - Help customers with their orders, returns, and product issues
        - Use customer context to provide personalized support
        - Search for product information when needed
        - Be empathetic and solution-focused
        - Reference previous orders and preferences when relevant
        
        Always be professional, helpful, and aim to resolve customer issues efficiently."""
    )

    print("✅ Customer support agent created with memory capabilities")

    # Seed with previous customer interactions
    previous_interactions = [
        ("I bought a new iPhone 15 Pro on June 1st, 2025. Order number is 123456.", "USER"),
        ("Thank you for your purchase! I can see your iPhone 15 Pro order #123456 was delivered successfully. How can I help you today?", "ASSISTANT"),
        ("I also ordered Sennheiser headphones on June 20th. Order number 654321. They came with 1-year warranty.", "USER"),
        ("Perfect! I have your Sennheiser headphones order #654321 on file with the 1-year warranty. Both your iPhone and headphones should work great together.", "ASSISTANT"),
        ("I'm looking for a good laptop. I prefer ThinkPad models.", "USER"),
        ("Great choice! ThinkPads are excellent for their durability and performance. Let me help you find the right model for your needs.", "ASSISTANT")
    ]

    # Save previous interactions
    try:
        client.create_event(
            memory_id=memory_id,
            actor_id=CUSTOMER_ID,
            session_id="previous_session",
            messages=previous_interactions
        )
        print("✅ Seeded customer history")
    except Exception as e:
        print(f"⚠️ Error seeding history: {e}")
    
    # Interactive loop for user queries
    while True:
        try:
            query = input("\nEnter your support query (or 'quit' to exit): ")
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            # Display customer memory summary
            print("\n📚 Customer Memory Summary:")
            print("=" * 50)
            
            namespaces_dict = get_namespaces(client, memory_id)
            for context_type, namespace_template in namespaces_dict.items():
                namespace = namespace_template.replace("{actorId}", CUSTOMER_ID)
                
                try:
                    memories = client.retrieve_memories(
                        memory_id=memory_id,
                        namespace=namespace,
                        query="customer orders and preferences",
                        top_k=3
                    )
                    
                    print(f"\n{context_type.upper()} ({len(memories)} items):")
                    for i, memory in enumerate(memories, 1):
                        if isinstance(memory, dict):
                            content = memory.get('content', {})
                            if isinstance(content, dict):
                                text = content.get('text', '')[:150] + "..."
                                print(f"  {i}. {text}")
                                
                except Exception as e:
                    print(f"Error retrieving {context_type} memories: {e}")
            
            print("\n" + "=" * 50)
            
            response = support_agent(query)
            print(f"\nSupport Agent: {response}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
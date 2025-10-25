import json

from strands import Agent, tool
from strands_tools import calculator, current_time

# Import the AgentCore SDK
from bedrock_agentcore.runtime import BedrockAgentCoreApp

WELCOME_MESSAGE = """
Welcome to the Customer Support Assistant! How can I help you today?
"""

SYSTEM_PROMPT = """
You are an helpful customer support assistant.
When provided with a customer email, gather all necessary info and prepare the response email.
When asked about an order, look for it and tell the full description and date of the order to the customer.
Don't mention the customer ID in your reply.
"""

@tool
def get_customer_id(email_address: str) -> str:
    "Get customer ID from email address"
    if email_address == "me@example.net":
        response = { "customer_id": 123 }
    else:
        response = { "message": "customer not found" }
    try:
        return json.dumps(response)
    except Exception as e:
        return str(e)


@tool
def get_orders(customer_id: int) -> str:
    "Get orders from customer ID"
    if customer_id == 123:
        response = [{
            "order_id": 1234,
            "items": [ "smartphone", "smartphone USB-C charger", "smartphone black cover"],
            "date": "20250607"
        }]
    else:
        response = { "message": "no order found" }
    try:
        return json.dumps(response)
    except Exception as e:
        return str(e)

@tool
def get_knowledge_base_info(topic: str) -> str:
    "Get knowledge base info from topic"
    response = []
    if "smartphone" in topic:
        if "cover" in topic:
            response.append("To put on the cover, insert the bottom first, then push from the back up to the top.")
            response.append("To remove the cover, push the top and bottom of the cover at the same time.")
        if "charger" in topic:
            response.append("Input: 100-240V AC, 50/60Hz")
            response.append("Includes US/UK/EU plug adapters")
    if len(response) == 0:
        response = { "message": "no info found" }
    try:
        return json.dumps(response)
    except Exception as e:
        return str(e)

# Create an AgentCore app
app = BedrockAgentCoreApp()

agent = Agent(
    model="us.amazon.nova-lite-v1:0",
    system_prompt=SYSTEM_PROMPT,
    tools=[calculator, current_time, get_customer_id, get_orders, get_knowledge_base_info]
)

# Specify the entry point function invoking the agent
@app.entrypoint
def invoke(payload):
    """Handler for agent invocation"""
    user_message = payload.get(
        "prompt", "No prompt found in input, please guide customer to create a json payload with prompt key"
    )
    response = agent(user_message)
    return response.message['content'][0]['text']
    
if __name__ == "__main__":
    app.run()

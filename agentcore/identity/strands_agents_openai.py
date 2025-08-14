import asyncio
from bedrock_agentcore.identity.auth import requires_access_token, requires_api_key
from strands import Agent, tool
from strands_tools import calculator 
import argparse
import json
from strands.models.litellm import LiteLLMModel
import os
from bedrock_agentcore.runtime import BedrockAgentCoreApp

OPENAI_API_KEY_FROM_CREDS_PROVIDER = ""

@requires_api_key(
    provider_name="openai-apikey-provider" # replace with your own credential provider name
)
async def need_api_key(*, api_key: str):
    global OPENAI_API_KEY_FROM_CREDS_PROVIDER
    print(f'received api key for async func: {api_key}')
    OPENAI_API_KEY_FROM_CREDS_PROVIDER = api_key

app = BedrockAgentCoreApp()

# Create a custom tool 
@tool
def weather():
    """ Get weather """ # Dummy implementation
    return "sunny"

# Global agent variable
agent = None

@app.entrypoint
async def strands_agent_open_ai(payload):
    """
    Invoke the agent with a payload
    """
    global OPENAI_API_KEY_FROM_CREDS_PROVIDER, agent
    
    print(f"Entrypoint called with OPENAI_API_KEY_FROM_CREDS_PROVIDER: '{OPENAI_API_KEY_FROM_CREDS_PROVIDER}'")
    
    # Get API key if not already retrieved
    if not OPENAI_API_KEY_FROM_CREDS_PROVIDER:
        print("Attempting to retrieve API key...")
        try:
            await need_api_key(api_key="")
            print(f"API key retrieved: '{OPENAI_API_KEY_FROM_CREDS_PROVIDER}'")
            os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY_FROM_CREDS_PROVIDER
            print("Environment variable OPENAI_API_KEY set")
        except Exception as e:
            print(f"Error retrieving API key: {e}")
            raise
    else:
        print("API key already available")
    
    # Initialize agent after API key is set
    if agent is None:
        print("Initializing agent with API key...")
        model = "openai/gpt-3.5-turbo"
        litellm_model = LiteLLMModel(
            model_id=model, params={"max_tokens": 4096, "temperature": 0.7}
        )
        
        agent = Agent(
            model=litellm_model,
            tools=[calculator, weather],
            system_prompt="You're a helpful assistant. You can do simple math calculation, and tell the weather."
        )
        print("Agent initialized successfully")
    
    user_input = payload.get("prompt")
    print(f"User input: {user_input}")
    
    try:
        response = agent(user_input)
        print(f"Agent response: {response}")
        return response.message['content'][0]['text']
    except Exception as e:
        print(f"Error in agent processing: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    app.run(port=args.port)
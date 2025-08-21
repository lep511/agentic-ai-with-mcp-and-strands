#!/usr/bin/env python

# This code has been adapted from:
# https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/02-AgentCore-gateway/01-transform-lambda-into-mcp-tools/01-gateway-target-lambda.ipynb

import json
import logging
import os
import sys

from dotenv import load_dotenv
from mcp.client.streamable_http import streamablehttp_client 
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient

# Add '..' folder to path, which is expected to contain agencore_utils.py
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)
print(f'Added path: {parent_path}')

import agentcore_utils


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logging.getLogger("strands").setLevel(logging.INFO)


# Load environment variables
load_dotenv()

REGION = os.getenv('AWS_REGION', 'us-west-2')
USER_POOL_ID = os.getenv('USER_POOL_ID')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
SCOPE_STRING = os.getenv('SCOPE_STRING')
gatewayURL = os.getenv('GATEWAY_URL')
targetname='LambdaUsingSDK'


# Setup Cognito
def get_cognito_token(user_pool_id, client_id, client_secret, scopeString):
    """
    Retrieves an access token from Amazon Cognito for authorization.
    
    Args:
        user_pool_id (str): ID of the Cognito user pool
        client_id (str): ID of the client
        client_secret (str): Secret for the client
        scopeString (str): Scopes for the token
        REGION (str): AWS region
        
    Returns:
        dict: Token response containing the access token
    """

    print("Requesting the access token from Amazon Cognito authorizer...")
    token_response = agentcore_utils.get_token(user_pool_id, client_id, client_secret, scopeString, REGION)
    return token_response["access_token"]

cognito_token = get_cognito_token(
    user_pool_id = USER_POOL_ID,
    client_id = CLIENT_ID,
    client_secret = CLIENT_SECRET,
    scopeString = SCOPE_STRING
)
print(f"Cogito Token:\n{cognito_token}\n")


# Setup MCP
def create_streamable_http_transport():
    """
    Creates and returns a streamable HTTP transport client for MCP communication.
    
    Uses the configured gateway URL and adds Cognito authentication token to request headers.
    
    Returns:
        streamablehttp_client: Configured HTTP client for making MCP requests
    """
    return streamablehttp_client(gatewayURL,headers={"Authorization": f"Bearer {cognito_token}"})


def invoke_agentcore_gateway():
    """
    Invokes the AgentCore gateway to interact with tools and models.
    
    This function:
    1. Creates an MCP client with streamable HTTP transport
    2. Lists available tools
    3. Creates an agent with the configured model and tools
    4. Demonstrates tool invocation through:
       - Listing available tools via agent prompt
       - Checking order status via agent prompt
       - Direct MCP tool call for order status
    
    Returns:
        None
    """

    http_client = MCPClient(create_streamable_http_transport)

    with http_client:
        # Call the listTools 
        tools = http_client.list_tools_sync()

        # Create an Agent with the model and tools
        agent = Agent(
            model = model,
            tools = tools
        )
        print(f"Tools loaded in the agent are {agent.tool_names}")

        # Invoke the agent with the sample prompt. This will only invoke 
        # MCP listTools and retrieve the list of tools the LLM has access to.
        # The below does not actually call any tool.
        agent("Hi, can you list all tools available to you")

        # Invoke the agent with sample prompt, invoke the tool and display the response
        agent("Check the order status for order id 123 and show me the exact response from the tool")

        # Call the MCP tool explicitly. The MCP Tool name and arguments must match with your AWS Lambda function or the OpenAPI/Smithy API
        result = http_client.call_tool_sync(
            tool_use_id="get-order-id-123-call-1", # You can replace this with unique identifier.
            name=targetname+"___get_order_tool",   # This is the tool name based on AWS Lambda target types. This will change based on the target name
            arguments={"orderId": "123"}
        )
        # Print the MCP Tool response
        tool_call_result = json.loads(result['content'][0]['text'])
        print(f"\nTool Call result:\n{json.dumps(tool_call_result, indent=2, default=str)}")


def main():
    invoke_agentcore_gateway()


model = BedrockModel(
    model_id="us.amazon.nova-pro-v1:0",
    temperature=0.7,
)

if __name__ == "__main__":
    main()

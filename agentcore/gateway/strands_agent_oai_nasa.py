import os
import logging
from strands.models import BedrockModel
from mcp.client.streamable_http import streamablehttp_client 
from strands.tools.mcp.mcp_client import MCPClient
from strands import Agent

def create_streamable_http_transport():
    gatewayURL = os.environ.get('GATEWAY_URL')
    token = os.environ.get('ACCESS_TOKEN')
    
    if not gatewayURL or not token:
        raise ValueError(f"Missing environment variables: GATEWAY_URL={gatewayURL}, ACCESS_TOKEN={'set' if token else 'not set'}")
    
    print(f"Connecting to: {gatewayURL}")
    print(f"Token length: {len(token)}")
    return streamablehttp_client(gatewayURL, headers={"Authorization": f"Bearer {token}"})

client = MCPClient(create_streamable_http_transport)

yourmodel = BedrockModel(
    model_id="us.amazon.nova-pro-v1:0",
    temperature=0.7,
)

logging.getLogger("strands").setLevel(logging.INFO)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s", 
    handlers=[logging.StreamHandler()]
)

with client:
    tools = client.list_tools_sync()
    agent = Agent(model=yourmodel, tools=tools)
    print(f"Tools loaded in the agent are {agent.tool_names}")
    
    agent("Hi, can you list all tools available to you")
    agent("What is the weather in northern part of the mars")
    
    targetname = os.environ.get('TARGET_NAME')
    result = client.call_tool_sync(
        tool_use_id="get-insight-weather-1",
        name=targetname + "___getInsightWeather",
        arguments={"ver": "1.0", "feedtype": "json"}
    )
    print(f"Tool Call result: {result['content'][0]['text']}")
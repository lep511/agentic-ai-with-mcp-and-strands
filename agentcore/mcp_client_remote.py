"""
AWS Bedrock Agent Runtime Interaction Script

This script interacts with AWS Bedrock Agent Runtime service to list and invoke agents.
It handles authentication via bearer token and automatically discovers agent runtimes
if not explicitly specified.

Environment Variables:
    AWS_REGION (str): AWS region to use (defaults to us-west-2)
    AGENT_ARN (str): ARN of the agent runtime to use (optional)
    BEARER_TOKEN (str): Bearer token for authentication (required)

Dependencies:
    - boto3
    - python-dotenv
    - mcp
"""

import asyncio
import boto3
import os
import sys

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()

region = os.getenv('AWS_REGION', 'us-west-2')
print(f'Using region: {region}')

# Automatically get the ARN from the first AgentCore Runtime
agentcore_control_client = boto3.client(
    'bedrock-agentcore-control',
    region_name=region
)

def get_agent_runtimes():
    response = agentcore_control_client.list_agent_runtimes()
    return [ runtime for runtime in response['agentRuntimes'] ]

agent_arn = os.getenv('AGENT_ARN', None)
bearer_token = os.getenv('BEARER_TOKEN', None)

if agent_arn is None:
    runtimes = get_agent_runtimes()
    agent_arns = [ runtime['agentRuntimeArn'] for runtime in runtimes ]
    if len(agent_arns):
        agent_arn = agent_arns[0]
        print(f"Using the first agent ARN: {agent_arn}")
    else:
        print("No agent runtimes found")
        sys.exit(1)

if not bearer_token:
    print("Error: BEARER_TOKEN environment variable is not set")
    sys.exit(1)

print(f'Agent ARN: {agent_arn}')
print(f'Bearer Token: {bearer_token}')


async def main():    
    encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
    mcp_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    headers = {"authorization": f"Bearer {bearer_token}","Content-Type":"application/json"}
    print(f"Invoking: {mcp_url}, \nwith headers: {headers}\n")

    async with streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tool_result = await session.list_tools()
            print(tool_result)

asyncio.run(main())

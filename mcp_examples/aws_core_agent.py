#!/usr/bin/env python

"""
AWS Core MCP Server Demo

MCP server that provides a starting point for using AWS MCP servers through a dynamic proxy server strategy based on role-based environment variables.

Features
- Planning and orchestration
  - Provides tool for prompt understanding and translation to AWS services
- Dynamic Proxy Server Strategy
  - The Core MCP Server implements a proxy server strategy that dynamically imports and proxies other MCP servers based on role-based environment variables. This allows you to create tailored server configurations for specific use cases or roles without having to manually configure each server.
  - Benefits of the Proxy Server Strategy
    Simplified Configuration: Enable multiple servers with a single environment variable
    Reduced Duplication: Servers are imported only once, even if needed by multiple roles
    Tailored Experience: Create custom server configurations for specific use cases
    Flexible Deployment: Easily switch between different server configurations

Usage Notes
- If no roles are enabled, the Core MCP Server will still provide its basic functionality (prompt_understanding) but won't import any additional servers
- You can enable multiple roles simultaneously to create a comprehensive server configuration
- The proxy strategy ensures that each server is imported only once, even if it's needed by multiple roles

Reference
- https://github.com/awslabs/mcp/tree/main/src/core-mcp-server
- https://github.com/awslabs/mcp/blob/main/src/core-mcp-server/awslabs/core_mcp_server/static/PROMPT_UNDERSTANDING.md
"""


import logging
import os

from botocore.config import Config
from mcp import stdio_client, StdioServerParameters
from shutil import which

from strands import Agent
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.models.bedrock import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logging.getLogger("strands").setLevel(logging.INFO)

HOME = os.getenv('HOME')
BEDROCK_REGION = os.getenv("BEDROCK_REGION", 'us-west-2')
BEDROCK_MODEL_ID = "us.amazon.nova-lite-v1:0"

# AWS Core MCP Server
stdio_mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(
        command = which('uvx'),
        args = [ 'awslabs.core-mcp-server@latest' ],
        env = {
          "FASTMCP_LOG_LEVEL": os.getenv('FASTMCP_LOG_LEVEL', 'ERROR'),
          "aws-foundation": "true",
          "solutions-architect": "true"
        },
        autoApprove = [],
        disabled = False
    )
))

# Initialize Strands Agent
model = BedrockModel(
    model_id = BEDROCK_MODEL_ID,
    max_tokens = 2048,
    boto_client_config = Config(
        read_timeout = 120,
        connect_timeout = 120,
        retries = dict(max_attempts=3, mode="adaptive"),
    ),
    temperature = 0.1
)

AWS_CORE_SYSTEM_PROMPT = """
You are an AWS core MCP server that helps developers understand AWS services and best practices.
You provide clear, accurate guidance on AWS service usage, configuration, and troubleshooting.
You should:
- Give step-by-step instructions when explaining processes
- Include relevant AWS CLI commands or code examples when appropriate 
- Reference official AWS documentation when possible
- Focus on AWS best practices and security recommendations
- Be clear about any prerequisites or dependencies
"""

prompts = [
    "How do I create an S3 bucket?",
    "What can I update my Lambda function code that I've created?",
    "How may I set up VPC flow logging?"
]

def main():
    with stdio_mcp_client:
        tools = stdio_mcp_client.list_tools_sync()
        aws_core_agent = Agent(
            system_prompt = AWS_CORE_SYSTEM_PROMPT,
            model = model,
            tools = tools,
            callback_handler = PrintingCallbackHandler()
        )

        # Interactive loop
        print('------------------------')
        print('AWS Core MCP Server Demo')
        print('------------------------')
        print('\nExample prompts to try:')
        print('\n'.join(['- ' + p for p in prompts]))
        print("\nType 'exit' to quit.\n")

        while True:
            user_input = input("Question: ")

            if user_input.lower() in ["exit", "quit"]:
                break

            print("\nThinking...\n")
            response = aws_core_agent(user_input)
            print('\n' + '-' * 80 + '\n')

if __name__ == '__main__':
    main()

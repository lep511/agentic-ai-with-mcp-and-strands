#!/usr/bin/env python

"""
AWS Core MCP Server Demo

A command-line interface that uses Strands and Bedrock to provide AWS service guidance.
Connects to an AWS Core MCP server to answer questions about AWS services and best practices.

The script:
- Sets up logging and environment configuration
- Initializes a Bedrock model client
- Creates an interactive CLI loop to handle user questions
- Uses a system prompt focused on AWS service guidance
- Provides example prompts for common AWS tasks
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

# AWS Documentation MCP Server
stdio_mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(
        command = which('uvx'),
        args = [ 'awslabs.core-mcp-server@latest' ],
        env = {
          "FASTMCP_LOG_LEVEL": "ERROR",
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

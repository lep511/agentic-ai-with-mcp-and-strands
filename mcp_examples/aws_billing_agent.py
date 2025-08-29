#!/usr/bin/env python

"""
AWS Billing MCP Server Demo

A command-line interface for interacting with AWS billing and cost management services using MCP.
Leverages Strands Agent and Bedrock model for natural language processing of billing queries.

Tools:
- cost-explorer
- compute-optimizer
- cost-optimization
- storage-lens
- pricing
- budget
- cost-anomaly
- cost-comparison
- free-tier-usage
- rec-details
- ri-performance
- sp-performance
- session-sql

References:
- https://github.com/awslabs/mcp/tree/main/src/billing-cost-management-mcp-server
- https://github.com/awslabs/mcp/blob/main/src/billing-cost-management-mcp-server/awslabs/billing_cost_management_mcp_server/server.py
"""


import logging
import os

from botocore.config import Config
from mcp import stdio_client, StdioServerParameters
from shutil import which

from strands import Agent
from strands_tools import current_time
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
BEDROCK_MODEL_ID = "us.amazon.nova-pro-v1:0"

# AWS Documentation MCP Server
stdio_mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(
        command = which('uvx'),
        args = [ 'awslabs.billing-cost-management-mcp-server@latest' ],
        env = {
          "FASTMCP_LOG_LEVEL": os.getenv('FASTMCP_LOG_LEVEL', 'ERROR'),
          "AWS_PROFILE": os.getenv('AWS_PROFILE', 'default'),
          "AWS_REGION": os.getenv('AWS_REGION', os.getenv('AWS_DEFAULT_REGION', 'us-west-2'))
        },
        disabled = False,
        autoApprove = []
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

AWS_BILLING_SYSTEM_PROMPT = """
You are an AWS billing MCP server that helps users understand and analyze their AWS costs and usage.

Your capabilities include:
- Retrieving cost and usage data from AWS Cost Explorer
- Analyzing billing trends and patterns 
- Providing cost optimization recommendations
- Breaking down costs by service, region, and tags
- Explaining billing concepts and terminology
- Helping with budgets and forecasting
- Identifying cost anomalies and unusual spending patterns
- Analyzing Reserved Instance and Savings Plan performance
- Monitoring Free Tier usage and limits
- Generating cost comparison reports
- Providing storage optimization insights via Storage Lens
- Running cost analysis queries using session SQL

Please provide clear, concise responses focused on billing and cost management.
When using Cost Explorer APIs, format monetary values appropriately and specify the currency.
If you need clarification on a query, ask follow-up questions to better understand the user's needs.
For optimization recommendations, prioritize them by potential cost savings impact.
"""

prompts = [
    "What is my AWS cost for this month?",
    "Help me understand my EC2 costs in us-west-2",
]

def main():
    with stdio_mcp_client:
        tools = stdio_mcp_client.list_tools_sync()
        aws_billing_agent = Agent(
            system_prompt = AWS_BILLING_SYSTEM_PROMPT,
            model = model,
            tools = tools + [current_time],
            callback_handler = PrintingCallbackHandler()
        )

        # Interactive loop
        print('---------------------------')
        print('AWS Billing MCP Server Demo')
        print('---------------------------')
        print('\nExample prompts to try:')
        print('\n'.join(['- ' + p for p in prompts]))
        print("\nType 'exit' to quit.\n")

        while True:
            user_input = input("Question: ")

            if user_input.lower() in ["exit", "quit"]:
                break

            print("\nThinking...\n")
            try:
                response = aws_billing_agent(user_input)
            except Exception as e:
                print(f"\nException: {e}")
                continue
            print('\n' + '-' * 80 + '\n')

if __name__ == '__main__':
    main()

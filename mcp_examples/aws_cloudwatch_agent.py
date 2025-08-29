#!/usr/bin/env python

"""
AWS Labs Cloudwatch MCP Server
==============================

This AWS Labs Model Context Protocol (MCP) server for CloudWatch enables your troubleshooting agents to use CloudWatch data to do AI-powered root cause analysis and provide recommendations. It offers comprehensive observability tools that simplify monitoring, reduce context switching, and help teams quickly diagnose and resolve service issues. This server will provide AI agents with seamless access to CloudWatch telemetry data through standardized MCP interfaces, eliminating the need for custom API integrations and reducing context switching during troubleshooting workflows. By consolidating access to all CloudWatch capabilities, we enable powerful cross-service correlations and insights that accelerate incident resolution and improve operational visibility.

The CloudWatch MCP Server provides specialized tools to address common operational scenarios including alarm troubleshooting, understand metrics definitions, alarm recommendations and log analysis. Each tool encapsulates one or multiple CloudWatch APIs into task-oriented operations.

Features
- Alarm Based Troubleshooting - Identifies active alarms, retrieves related metrics and logs, and analyzes historical alarm patterns to determine root causes of triggered alerts. Provides context-aware recommendations for remediation.
- Log Analyzer - Analyzes a CloudWatch log group for anomalies, message patterns, and error patterns within a specified time window.
- Metric Definition Analyzer - Provides comprehensive descriptions of what metrics represent, how they're calculated, recommended statistics to use for metric data retrieval
- Alarm Recommendations - Suggests recommended alarm configurations for CloudWatch metrics, including thresholds, evaluation periods, and other alarm settings.

Usage:
    python cloudwatch_mcp_server.py [-v/--verbose]

Options:
    -v, --verbose   Enable verbose logging

Environment Variables:
    BEDROCK_REGION          AWS region for Bedrock (default: us-west-2)
    BEDROCK_MODEL_ID        Bedrock model ID (default: us.amazon.nova-lite-v1:0)
    FASTMCP_LOG_LEVEL       Sets logging level for FastMCP (default: ERROR)

Reference:
- Github: https://github.com/awslabs/mcp/tree/main/src/cloudwatch-mcp-server
- Server: https://github.com/awslabs/mcp/blob/main/src/cloudwatch-mcp-server/awslabs/cloudwatch_mcp_server/server.py
- Tools (Alarms): https://github.com/awslabs/mcp/blob/main/src/cloudwatch-mcp-server/awslabs/cloudwatch_mcp_server/cloudwatch_alarms/tools.py
- Tools (Logs): https://github.com/awslabs/mcp/blob/main/src/cloudwatch-mcp-server/awslabs/cloudwatch_mcp_server/cloudwatch_logs/tools.py
- Tools (Metrics): https://github.com/awslabs/mcp/blob/main/src/cloudwatch-mcp-server/awslabs/cloudwatch_mcp_server/cloudwatch_metrics/tools.py
"""


import argparse
import logging
import os
import sys

from botocore.config import Config
from mcp import stdio_client, StdioServerParameters
from shutil import which
from typing import List

from strands import Agent
from strands_tools import current_time
from strands.models.bedrock import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from strands.handlers.callback_handler import PrintingCallbackHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logging.getLogger("strands").setLevel(logging.INFO)
logging.getLogger("strands.agent").setLevel(logging.INFO)
logging.getLogger("strands.event_loop").setLevel(logging.INFO)
logging.getLogger("strands.handlers").setLevel(logging.INFO)
logging.getLogger("strands.models").setLevel(logging.INFO)
logging.getLogger("strands.tools").setLevel(logging.INFO)
logging.getLogger("strands.types").setLevel(logging.INFO)

# Configuration with environment variable fallbacks
HOME = os.getenv('HOME')
PWD = os.getenv('PWD', os.getcwd())
BEDROCK_REGION = os.getenv("BEDROCK_REGION", 'us-west-2')
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")


def create_mcp_client() -> MCPClient:

    """
    Create an MCP client for the AWS CloudWatch MCP Server.
    
    Creates and configures an MCP client that connects to the AWS CloudWatch MCP Server.
    The client uses stdio transport and requires the uvx command to be installed.
    
    Args:
        None
        
    Returns:
        MCPClient: Configured MCP client instance ready to connect to AWS CloudWatch MCP Server
        
    Raises:
        RuntimeError: If the required uvx command is not found in the system path
        
    Environment Variables:
        FASTMCP_LOG_LEVEL: Sets the logging level for FastMCP (default: ERROR)
    """

    cmd = which('uvx')
    if not cmd:
        raise RuntimeError("uvx command not found. Please install uvx.")
    return MCPClient(lambda: stdio_client(
        StdioServerParameters(
            command=cmd,
            args=[
                'awslabs.cloudwatch-mcp-server@latest'
            ],
            autoApprove=[],
            disabled=False,
            env={
                # 'AWS_PROFILE': '[The AWS Profile name to use (e.g. default)]',
                'FASTMCP_LOG_LEVEL': os.getenv('FASTMCP_LOG_LEVEL', 'ERROR')
            },
            transportType='stdio'
        )
    ))

def create_bedrock_model(model_id: str, region: str, temperature: float = 0.1) -> BedrockModel:
    """Create a Bedrock model with appropriate configuration.
    
    Args:
        model_id: The Bedrock model ID to use
        region: AWS region for Bedrock
        temperature: Model temperature (lower is more deterministic)
        
    Returns:
        BedrockModel: Configured Bedrock model
    """
    return BedrockModel(
        model_id=model_id,
        max_tokens=2048,
        boto_client_config=Config(
            region_name=region,
            read_timeout=120,
            connect_timeout=120,
            retries=dict(max_attempts=3, mode="adaptive"),
        ),
        temperature=temperature
    )

AWS_CLOUDWATCH_SYSTEM_PROMPT = """You are an AI assistant specialized in AWS CloudWatch monitoring and observability.
Your role is to help users analyze CloudWatch metrics, logs, and alarms to
troubleshoot issues and provide actionable insights.

You have access to CloudWatch data through specialized tools that allow you to:
- Investigate active alarms and their root causes
- Analyze CloudWatch log groups for patterns and anomalies
- Understand metric definitions and recommended usage
- Suggest optimal alarm configurations

When responding:
1. Focus on providing clear, actionable insights based on the CloudWatch data
2. Explain your analysis and recommendations in a clear, structured way
3. Use CloudWatch best practices and AWS recommended monitoring approaches
4. Cite specific metrics, logs, or alarms that support your conclusions
5. Suggest next steps or additional areas to investigate when relevant

Your goal is to help users quickly understand and resolve operational issues using CloudWatch data
while following AWS monitoring best practices.
"""

prompts = [
    "Describe my log groups in us-west-2",
    "What are my CloudWatch alarms in us-west-2"
]

def run_interactive_session(agent: Agent, example_prompts: List[str]) -> None:
    """Run an interactive session with the AWS CloudWatch Agent.
    
    Args:
        agent: The configured Strands Agent
        example_prompts: List of example prompts to show the user
    """
    print('-------------------------')
    print('AWS CloudWatch Agent Demo')
    print('-------------------------')
    print('\nExample prompts to try:')
    print('\n'.join(['- ' + p for p in example_prompts]))
    print("\nType 'exit' to quit.\n")

    while True:
        try:
            user_input = input("Question: ")

            if user_input.lower() in ["exit", "quit"]:
                break

            print("\nThinking...\n")
            response = agent(user_input)
            print('\n' + '-' * 80 + '\n')
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def main(verbose: bool = True) -> None:
    """Main entry point for the AWS CloudWatch MCP Server demo.
    
    This function initializes and runs an interactive session with the AWS CloudWatch Agent.
    It sets up logging, creates an MCP client and Bedrock model, and starts a command line
    interface for users to interact with CloudWatch data.
    
    Args:
        verbose: If True, enables debug level logging for the strands library
        
    Raises:
        Exception: If there is an error initializing the AWS CloudWatch Agent
    """
    
    try:
        # Create MCP client
        mcp_client = create_mcp_client()
        
        # Create Bedrock model
        model = create_bedrock_model(
            model_id=BEDROCK_MODEL_ID,
            region=BEDROCK_REGION
        )
        
        with mcp_client:
            # Get available tools
            tools = mcp_client.list_tools_sync()
            
            # Create agent with callback handler for better visibility
            aws_cloudwatch_agent = Agent(
                system_prompt = AWS_CLOUDWATCH_SYSTEM_PROMPT,
                model = model,
                tools = tools + [current_time],
                callback_handler = PrintingCallbackHandler()
            )
            
            # Run interactive session
            run_interactive_session(aws_cloudwatch_agent, prompts)
            
    except Exception as e:
        logger.error(f"Error initializing AWS CloudWatch Agent: {e}")
        sys.exit(1)

def parse_args():
    """Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(description="AWS CloudWatch MCP Server Demo")
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    main(verbose=args.verbose)

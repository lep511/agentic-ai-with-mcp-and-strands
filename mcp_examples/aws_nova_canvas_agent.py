#!/usr/bin/env python

"""
AWS Nova Canvas MCP Server
========================

The AWS Nova Canvas Model Context Protocol (MCP) Server is a MCP server for generating images using Amazon Nova Canvas

Features
- Text-based image generation
- Create images from text prompts with generate_image
- Customizable dimensions (320-4096px), quality options, and negative prompting
- Supports multiple image generation (1-5) in single request
- Adjustable parameters like cfg_scale (1.1-10.0) and seeded generation

Color-guided image generation
- Generate images with specific color palettes using generate_image_with_colors
- Define up to 10 hex color values to influence the image style and mood
- Same customization options as text-based generation

Workspace integration
- Images saved to user-specified workspace directories with automatic folder creation

AWS authentication
- Uses AWS profiles for secure access to Amazon Nova Canvas services

Prerequisites
1. Install uv from Astral or the GitHub README
2. Install Python using uv python install 3.10+
3. Set up AWS credentials with access to Amazon Bedrock and Nova Canvas
   - You need an AWS account with Amazon Bedrock and Amazon Nova Canvas enabled
   - Configure AWS credentials with aws configure or environment variables
   - Ensure your IAM role/user has permissions to use Amazon Bedrock and Nova Canvas
4. Output directory must be created (default is ./output)

Common errors
- Running in a region where Nova Canvas is not available
- Not creating an output directory, or not having write permissions to the directory

Tools
- ...

References
- Github: https://github.com/awslabs/mcp/tree/main/src/nova-canvas-mcp-server
- Home Page: https://awslabs.github.io/mcp/servers/nova-canvas-mcp-server/

"""


import logging
import os
import sys

from botocore.config import Config
from mcp import stdio_client, StdioServerParameters
from shutil import which
from typing import List

from strands import Agent
from strands.models.bedrock import BedrockModel
from strands_tools import file_write
from strands.tools.mcp.mcp_client import MCPClient

# This import is correct - PrintingCallbackHandler is a class from strands.handlers.callback_handler module
# Used to provide visibility into agent execution by printing callback events
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
BEDROCK_REGION = os.getenv("BEDROCK_REGION", 'us-east-1')
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")
BEDROCK_CANVAS_MODEL_ID = os.getenv("BEDROCK_CANVAS_MODEL_ID", "us.amazon.bedrock-nova-canvas-v1:0")
# AWS_API_MCP_WORKING_DIR = os.getenv('AWS_API_MCP_WORKING_DIR', os.path.join(PWD, "api_mcp_server"))

# Ensure working directory exists
# os.makedirs(AWS_API_MCP_WORKING_DIR, exist_ok=True)

def create_mcp_client() -> MCPClient:
    """Create an MCP client for the AWS Nova Canvas MCP Server.
    
    Args:
        None
        
    Returns:
        MCPClient: Configured MCP client
        
    Raises:
        RuntimeError: If required command is not found
    """
    cmd = which('uvx')
    if not cmd:
        raise RuntimeError("uvx command not found. Please install uvx.")
    return MCPClient(lambda: stdio_client(
        StdioServerParameters(
            command=cmd,
            args=['awslabs.nova-canvas-mcp-server@latest'],
            env={
                # 'AWS_PROFILE': 'default',
                'AWS_REGION': BEDROCK_REGION,
                'FASTMCP_LOG_LEVEL': 'ERROR'
            },
            disabled=False,
            autoApprove=[]
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
            retries=dict(max_attempts=4, mode="adaptive"),
        ),
        temperature=temperature
    )


AWS_NOVA_CANVAS_SYSTEM_PROMPT = """
You are an AWS Nova Canvas assistant focused on image generation capabilities.

Use the available tools to:
- Generate images from text descriptions
- Create images with specific color palettes
- Configure image dimensions, quality and other parameters
- Save generated images to workspace directories
- Apply negative prompting and other advanced features

Provide accurate guidance on using AWS Nova Canvas for image generation tasks.
"""


prompts = [
    "Generate a majestic mountain landscape at golden hour, with dramatic clouds catching the warm sunset light, snow-capped peaks, and a crystal clear alpine lake reflecting the sky",
    "Create a sprawling cyberpunk metropolis at night with towering skyscrapers, holographic billboards, flying vehicles weaving between buildings, and neon lights reflecting off rain-slicked streets",
    "Generate an ethereal abstract art piece with swirling patterns of deep sapphire blue and metallic gold, cosmic nebula-like forms, and flowing liquid textures",
    "Create a dreamy portrait in loose watercolor style with soft edges, delicate color washes, expressive brush strokes, and gentle light illuminating the subject's features",
    "Generate a pristine tropical paradise with turquoise waters, swaying palm trees, powdery white sand, dramatic cloud formations, and gentle waves lapping at the shore during magic hour"
]


def run_interactive_session(agent: Agent, example_prompts: List[str]) -> None:
    """Run an interactive session with the AWS Nova Canvas Agent.
    
    Args:
        agent: The configured Strands Agent for Nova Canvas image generation
        example_prompts: List of example image generation prompts to show the user
    """
    print('------------------------')
    print('  AWS Nova Canvas Demo  ')
    print('------------------------')
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


def main():
    """
    Main entry point for the AWS Nova Canvas MCP Server demo.
    """

    logging.getLogger("strands").setLevel(logging.DEBUG)
    
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
            tools = mcp_client.list_tools_sync() + [file_write]
            print(f'Tools: {tools}')

            # Create agent with callback handler for better visibility
            nova_canvas_agent = Agent(
                system_prompt = AWS_NOVA_CANVAS_SYSTEM_PROMPT,
                model = model,
                tools = tools,
                callback_handler = PrintingCallbackHandler()
            )
            
            # Run interactive session
            run_interactive_session(nova_canvas_agent, prompts)
            
    except Exception as e:
        logger.error(f"Error initializing AWS Nova Canvas Agent: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

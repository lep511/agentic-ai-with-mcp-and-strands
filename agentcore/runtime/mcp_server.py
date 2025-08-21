"""
MCP Server Implementation

This module implements a Model Composition Protocol (MCP) server using FastMCP.
It provides basic mathematical and greeting functionality through exposed tools.

The server is configured to run in stateless HTTP mode and exposes the following tools:
- add_numbers: Adds two integers together and returns their sum
- multiply_numbers: Multiplies two integers together and returns their product
- greet_user: Returns a personalized greeting message with the provided name

Usage:
    Run this file directly to start the MCP server:
    $ python mcp_server.py

The server will listen on all interfaces (0.0.0.0) using streamable HTTP transport on port 8000.

Dependencies:
    - mcp.server.fastmcp: Required for implementing the MCP server
    - starlette.responses: Used for returning JSON responses

This code has been adapted from:
    https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html
"""

from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse

mcp = FastMCP(host="0.0.0.0", stateless_http=True)

@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

@mcp.tool()
def multiply_numbers(a: int, b: int) -> int:
    """Multiply two numbers together"""
    return a * b

@mcp.tool()
def greet_user(name: str) -> str:
    """Greet a user by name"""
    return f"Hello, {name}! Nice to meet you."

if __name__ == "__main__":
    # The server runs on port 8000 using streamable HTTP transport
    mcp.run(transport="streamable-http")

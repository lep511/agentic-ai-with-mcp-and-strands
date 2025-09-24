#!/usr/bin/env python3
"""
# Strands Agents with Persistence

This example demonstrates how to integrate the Strands Agents SDK with session management capabilities, specifically
using the `S3SessionManager` to persist agent state and conversation history across multiple interactions. It shows how
to maintain context and continuity even when the application restarts or when deployed in distributed environments.

## Prerequisites

Export the S3 bucket name for session storage:
```
export STRANDS_BUCKET_NAME=your-bucket-name
```

## Usage Examples

Basic usage:
```
$ python session_agent.py
> My name is John
Customer ID: c1
```
"""

import logging
import os

from strands import Agent
from strands.session.s3_session_manager import S3SessionManager

logger = logging.getLogger(__name__)


def handle(customer_id: str, prompt: str) -> None:
    """Handle user interaction with session persistence."""
    
    # Create S3 session manager with customer-specific prefix
    session_manager = S3SessionManager(
        session_id="s123",  # Fixed session ID for this example
        bucket=os.getenv("STRANDS_BUCKET_NAME"),  # S3 bucket from environment
        prefix=customer_id,  # Customer-specific prefix for data isolation
    )
    
    # Create agent with session management
    agent = Agent(session_manager=session_manager)
    
    # Process the user's prompt - state and messages are automatically persisted
    agent(prompt)


if __name__ == "__main__":
    print("\nSession Management\n")
    print("This example demonstrates using Strands Agents with session management\n")

    while True:
        try:
            prompt = input("\n> ")
            customer_id = input("\nCustomer ID: ")

            if prompt.lower() == "exit":
                print("\nGoodbye! 👋")
                break

            handle(customer_id, prompt)

        except KeyboardInterrupt:
            print("\n\nExecution interrupted. Exiting...")
            break

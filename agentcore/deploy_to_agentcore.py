#!/usr/bin/env python

"""
A script to deploy an Amazon Bedrock Agent Core runtime.

This script provides functionality to deploy and configure an Amazon Bedrock Agent Core runtime
with specified agent name and entry point. It handles the deployment process including:
- Configuring the runtime with required parameters
- Creating execution roles and ECR repositories automatically 
- Launching the runtime
- Monitoring deployment status

The code is built on the Amazon Bedrock Agent Core Starter Toolkit and requires valid AWS credentials.

Dependencies:
- bedrock_agentcore_starter_toolkit
- boto3

Usage:
uv run deploy_to_agentcore.py --agent_name <name> --entry_point <file>

This code has been adapted from:
https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/01-AgentCore-runtime/01-hosting-agent/01-strands-with-bedrock-model/runtime_with_strands_and_bedrock_models.ipynb
"""

import argparse
import time
from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session

boto_session = Session()
region = boto_session.region_name

agentcore_runtime = Runtime()

def wait_for_status():
    status_response = agentcore_runtime.status()
    status = status_response.endpoint['status']
    end_status = ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']
    while status not in end_status:
        time.sleep(10)
        status_response = agentcore_runtime.status()
        status = status_response.endpoint['status']
        print(status)

def deploy_agentcore(agent_name, entry_point, requirements_file = 'requirements.txt'):
    response = agentcore_runtime.configure(
        entrypoint=entry_point,
        auto_create_execution_role=True,
        auto_create_ecr=True,
        requirements_file=requirements_file,
        region=region,
        agent_name=agent_name
    )
    launch_result = agentcore_runtime.launch()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--agent_name', type=str, help='Name of the agent to deploy')
    parser.add_argument('--entry_point', type=str, help='Entry point file for the agent')
    args = parser.parse_args()

    deploy_agentcore(
        agent_name = args.agent_name,
        entry_point = args.entry_point
    )

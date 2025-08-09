"""
AWS Bedrock Agent Runtime Management Script

This script provides functionality to manage agent runtimes in AWS Bedrock Agent Core service.
It allows listing and deleting agent runtimes with interactive confirmation.

The script uses the AWS SDK (boto3) to interact with the Bedrock Agent Core services.
It requires appropriate AWS credentials and permissions to be configured.

Environment Variables:
    AWS_REGION: AWS region to use (defaults to us-west-2)

Functions:
    get_agent_runtimes(): Retrieves list of all agent runtimes
    delete_agent_runtimes(): Deletes agent runtimes with confirmation
"""

import boto3
import json
import os


region = os.getenv('AWS_REGION', 'us-west-2')
print(f'Using region: {region}')

agentcore_client = boto3.client(
    'bedrock-agentcore',
    region_name=region
)
agentcore_control_client = boto3.client(
    'bedrock-agentcore-control',
    region_name=region
)

def get_agent_runtimes():
    """
    Retrieves a list of all agent runtimes from the Bedrock Agent Core service.
    
    Returns:
        list: A list of dictionaries containing information about each agent runtime.
        Each dictionary contains details like agentRuntimeName and agentRuntimeId.
    """
    response = agentcore_control_client.list_agent_runtimes()
    return [ runtime for runtime in response['agentRuntimes'] ]


def delete_agent_runtimes():
    """
    Deletes agent runtimes from the Bedrock Agent Core service.
    
    Retrieves all agent runtimes and prompts for confirmation before deleting each one.
    Prints status messages indicating success or failure of each deletion operation.
    
    Returns:
        None
    """
    
    runtimes = get_agent_runtimes()
    for runtime in runtimes:
        runtime_name = runtime['agentRuntimeName']
        runtime_id = runtime['agentRuntimeId']
        print('-' * 80)
        print(f"Name: {runtime_name} (ID: {runtime_id})")
        confirm = input("Are you sure you want to delete this runtime? (y/n): ")
        if confirm.lower() != 'y':
            continue
        try:
            response = agentcore_control_client.delete_agent_runtime(
                agentRuntimeId=runtime_id
            )
            print(f"Successfully deleted runtime {runtime_name}")
        except Exception as e:
            print(f"Failed to delete runtime {runtime_name}: {str(e)}")
    print('-' * 80)


if __name__ == "__main__":
    delete_agent_runtimes()

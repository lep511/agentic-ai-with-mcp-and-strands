#!/usr/bin/env python

"""
AWS Bedrock AgentCore Runtime IAM Setup and Deployment Script

This script automates the setup and deployment of an AWS Bedrock AgentCore Runtime agent by:

1. Creating or retrieving an IAM role with required trust policy for bedrock-agentcore.amazonaws.com
2. Setting up IAM policies with permissions for:
   - Amazon ECR image access
   - CloudWatch Logs management
   - X-Ray tracing
   - CloudWatch metrics publishing
   - Bedrock model invocation
   - AgentCore workload access token management
3. Deploying an agent runtime using the configured IAM role and a container image from ECR

Prerequisites:
- AWS credentials configured with appropriate permissions
- Docker image pushed to Amazon ECR
- AWS CLI installed and configured

Environment Variables:
    AWS_DEFAULT_REGION: Target AWS region (defaults to us-west-2)

Usage:
    python deploy_agent_from_ecr.py

The script will output:
- The ARN of the created/retrieved IAM role
- The agent runtime ARN
- The deployment status

Note: The executing role must have permissions to create/modify IAM roles and policies,
and must include 'bedrock-agentcore.amazonaws.com' in its trust policy.

Reference for trust policy and exeuction role permissions:
    https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html

"""

import argparse
import boto3
import json
import os
import time

from typing import Dict, Any

region = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')

iam = boto3.client('iam')
client = boto3.client('bedrock-agentcore-control', region_name=region)
sts = boto3.client('sts')
account_id = sts.get_caller_identity()['Account']


def generate_trust_policy(region: str, account_id: str) -> Dict[str, Any]:
    """Generate trust policy with source account and ARN conditions."""
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AssumeRolePolicy",
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock-agentcore.amazonaws.com"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": account_id
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"
                    }
                }
            }
        ]
    }

def create_agentcore_runtime_role(region: str, account_id: str, agent_name: str) -> Dict[str, Any]:
    """
    Creates an IAM role for AgentCore Runtime with the required permissions.
    
    Args:
        region: AWS region (e.g., 'us-east-1')
        account_id: AWS Account ID (e.g., '123456789012')
        agent_name: Agent name for workload identity resources
    
    Returns:
        Dict containing the created role information
    """
    
    trust_policy = generate_trust_policy(region, account_id)
    
    # Permissions policy
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ECRImageAccess",
                "Effect": "Allow",
                "Action": [
                    "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer"
                ],
                "Resource": [
                    f"arn:aws:ecr:{region}:{account_id}:repository/*"
                ]        
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:DescribeLogStreams",
                    "logs:CreateLogGroup"
                ],
                "Resource": [
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:DescribeLogGroups"
                ],
                "Resource": [
                    f"arn:aws:logs:{region}:{account_id}:log-group:*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": [
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
                ]
            },
            {
                "Sid": "ECRTokenAccess",
                "Effect": "Allow",
                "Action": [
                    "ecr:GetAuthorizationToken"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow", 
                "Action": [ 
                    "xray:PutTraceSegments", 
                    "xray:PutTelemetryRecords", 
                    "xray:GetSamplingRules", 
                    "xray:GetSamplingTargets"
                ],
                "Resource": ["*"] 
            },
            {
                "Effect": "Allow",
                "Resource": "*",
                "Action": "cloudwatch:PutMetricData",
                "Condition": {
                    "StringEquals": {
                        "cloudwatch:namespace": "bedrock-agentcore"
                    }
                }
            },
            {
                "Sid": "GetAgentAccessToken",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:GetWorkloadAccessToken",
                    "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                    "bedrock-agentcore:GetWorkloadAccessTokenForUserId"
                ],
                "Resource": [
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default",
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default/workload-identity/{agent_name}-*"
                ]
            },
            {
                "Sid": "BedrockModelInvocation", 
                "Effect": "Allow", 
                "Action": [ 
                    "bedrock:InvokeModel", 
                    "bedrock:InvokeModelWithResponseStream"
                ], 
                "Resource": [
                    "arn:aws:bedrock:*::foundation-model/*",
                    f"arn:aws:bedrock:{region}:{account_id}:*"
                ]
            }
        ]
    }
    
    role_name = f'agentcore-{agent_name}-role'
    
    try:
        # Create the role
        role_response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"AgentCore Runtime execution role for {agent_name}"
        )
        
        # Create and attach the policy
        policy_name = f"{agent_name}-agentcore-runtime-policy"
        policy_response = iam.create_policy(
            PolicyName=policy_name,
            PolicyDocument=json.dumps(permissions_policy),
            Description=f"AgentCore Runtime permissions for {agent_name}"
        )
        
        # Attach policy to role
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_response['Policy']['Arn']
        )
        
        return {
            'role_arn': role_response['Role']['Arn'],
            'role_name': role_name,
            'policy_arn': policy_response['Policy']['Arn'],
            'policy_name': policy_name
        }
        
    except Exception as e:
        print(f"Error creating role: {e}")
        raise


def get_agentcore_role_arn(role_name):
    try:
        response = iam.get_role(RoleName=role_name)
        # Role exists
        agentcore_iam_role = response['Role']['Arn']
        print(f'Using Agentcore IAM role: {agentcore_iam_role}')
    except iam.exceptions.NoSuchEntityException:
        # Role does not exist"
        response = create_agentcore_runtime_role(region, account_id, agent_name)
        agentcore_iam_role = response['role_arn']
        assert role_name == response['role_name']
        print(f'Created Agentcore IAM role: {role_name}')
        print(f'Role ARN: {agentcore_iam_role}')
        time.sleep(5)  # Wait 5 seconds to allow some time for the role permissions to propagate
    return agentcore_iam_role


def main(args):
    agentcore_iam_role = get_agentcore_role_arn(args.role_name)
    response = client.create_agent_runtime(
        agentRuntimeName=args.agent_name,
        agentRuntimeArtifact={
            'containerConfiguration': {
                'containerUri': args.container_uri
            }
        },
        networkConfiguration={"networkMode": "PUBLIC"},
        roleArn=agentcore_iam_role
    )

    print(f"Agent Runtime created successfully!")
    print(f"Agent Runtime ARN: {response['agentRuntimeArn']}")
    print(f"Status: {response['status']}")

# Set defaults
agent_name = 'strands_agent'
container_uri = f'{account_id}.dkr.ecr.{region}.amazonaws.com/my-strands-agent:latest'

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--agent-name', type=str, default=agent_name)
    parser.add_argument('--role-name', type=str, default=f'agentcore-{agent_name}-role')
    parser.add_argument('--container-uri', type=str, default=container_uri)
    args = parser.parse_args()
    main(args)

#!/usr/bin/env python

# This code has been adapted from:
# https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/02-AgentCore-gateway/01-transform-lambda-into-mcp-tools/01-gateway-target-lambda.ipynb

import boto3
import json
import os
import requests
import sys
import time

from botocore.exceptions import ClientError

# Add '..' folder to path, which is expected to contain agencore_utils.py
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)
print(f'Added path: {parent_path}')

import agentcore_utils


REGION = os.getenv('AWS_REGION', 'us-west-2')
USER_POOL_NAME = "sample-agentcore-gateway-pool"
RESOURCE_SERVER_ID = "sample-agentcore-gateway-id"
RESOURCE_SERVER_NAME = "sample-agentcore-gateway-name"
CLIENT_NAME = "sample-agentcore-gateway-client"

cognito = boto3.client("cognito-idp", region_name=REGION)
gateway_client = boto3.client('bedrock-agentcore-control', region_name = REGION)


def create_lambda_target(lambda_zip):
    """
    Creates a Lambda function from a zip file to be used as a gateway target.
    
    Args:
        lambda_zip (str): Path to the zip file containing the Lambda function code
        
    Returns:
        str: ARN of the created Lambda function
        
    Raises:
        Exception: If the zip file does not exist or Lambda creation fails
    """
    if not os.path.isfile(lambda_zip):
        raise Exception(f"Lambda function code zip file not found. Please ensure the file '{lambda_zip}' exists in the current directory.")

    lambda_resp = agentcore_utils.create_gateway_lambda(lambda_zip)
    print(json.dumps(lambda_resp, indent=2, default=str))

    if lambda_resp is not None:
        if lambda_resp['exit_code'] in [0, 1]:  # 0=created, 1=already exists
            lambda_arn = lambda_resp['lambda_function_arn']
            print(f"Lambda function ready with ARN: {lambda_arn}")
            return lambda_arn
        else:
            raise Exception("Lambda function creation failed with message: ", lambda_resp['lambda_function_arn'])


def create_gateway_role(role_name):
    """
    Creates an IAM role for the AgentCore gateway with required permissions.
    
    Args:
        role_name (str): Name to give the IAM role
        
    Returns:
        str: ARN of the created IAM role
        
    Raises:
        Exception: If role creation fails
    """
    agentcore_gateway_iam_role = agentcore_utils.create_agentcore_gateway_role(role_name)
    gateway_role_arn = agentcore_gateway_iam_role['Role']['Arn']
    print("Agentcore gateway role ARN: ", gateway_role_arn)
    return gateway_role_arn


def create_cognito_resources():
    """
    Creates or retrieves necessary Amazon Cognito resources for gateway authorization.
    
    This function:
    1. Creates/retrieves a Cognito user pool for Inbound authorization to Gateway
    2. Creates/retrieves a resource server with read/write scopes
    3. Creates/retrieves a machine-to-machine client
    4. Generates the Cognito discovery URL
    
    Returns:
        dict: Dictionary containing:
            - user_pool_id (str): ID of the Cognito user pool
            - client_id (str): ID of the created client
            - client_secret (str): Secret for the created client
            - cognito_discovery_url (str): URL for OpenID configuration
    """
    SCOPES = [
        {"ScopeName": "gateway:read", "ScopeDescription": "Read access"},
        {"ScopeName": "gateway:write", "ScopeDescription": "Write access"}
    ]
    scopeString = f'{RESOURCE_SERVER_ID}/gateway:read {RESOURCE_SERVER_ID}/gateway:write'
    print('Creating or retrieving Cognito resources...')
    user_pool_id = agentcore_utils.get_or_create_user_pool(cognito, USER_POOL_NAME)
    print(f'User Pool ID: {user_pool_id}')

    agentcore_utils.get_or_create_resource_server(cognito, user_pool_id, RESOURCE_SERVER_ID, RESOURCE_SERVER_NAME, SCOPES)
    print('Resource server ensured.')

    client_id, client_secret  = agentcore_utils.get_or_create_m2m_client(cognito, user_pool_id, CLIENT_NAME, RESOURCE_SERVER_ID)
    print(f'Client ID: {client_id}')

    # Get discovery URL  
    cognito_discovery_url = f'https://cognito-idp.{REGION}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration'
    print(f'Cognito Discovery URL: {cognito_discovery_url}')
    return {
        'user_pool_id': user_pool_id,
        'client_id': client_id,
        'client_secret': client_secret,
        'cognito_discovery_url': cognito_discovery_url,
        'scopeString': scopeString
    }


# Create the Gateway with Amazon Cognito Authorizer for inbound authorization
# - CreateGateway with Cognito authorizer without CMK.
# - Use the Cognito user pool created in the previous step

def create_agentcore_gateway(client_id, cognito_discovery_url, gateway_name, gateway_role_arn):
    """
    Creates an AgentCore gateway with Cognito JWT authorizer or returns existing one.

    Args:
        client_id (str): The Cognito client ID to allow access to the gateway
        cognito_discovery_url (str): The OpenID configuration discovery URL for the Cognito user pool
        gateway_name (str): Name to give the gateway
        gateway_role_arn (str): ARN of the IAM role for the gateway

    Returns:
        dict: Response from the create_gateway API call containing:
            - gatewayId (str): ID of the created gateway
            - gatewayUrl (str): URL endpoint for the gateway
            - gatewayArn (str): ARN of the created gateway

    Raises:
        ClientError: If gateway creation fails
    """
    auth_config = {
        "customJWTAuthorizer": { 
            "allowedClients": [client_id],  # Client MUST match with the ClientId configured in Cognito. Example: 7rfbikfsm51j2fpaggacgng84g
            "discoveryUrl": cognito_discovery_url
        }
    }
    
    try:
        create_response = gateway_client.create_gateway(
            name = gateway_name,
            roleArn = gateway_role_arn, # The IAM Role must have permissions to create/list/get/delete Gateway 
            protocolType = 'MCP',
            authorizerType = 'CUSTOM_JWT',
            authorizerConfiguration = auth_config, 
            description = 'AgentCore Gateway with AWS Lambda target type'
        )
        return create_response
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            print(f"Gateway '{gateway_name}' already exists. Finding existing gateway...")
            # List gateways to find the existing one
            response = gateway_client.list_gateways()
            for gateway in response.get('items', []):
                if gateway['name'] == gateway_name:
                    print(f"Found existing gateway: {gateway['gatewayId']}")
                    # Get full gateway details
                    full_gateway = gateway_client.get_gateway(gatewayIdentifier=gateway['gatewayId'])
                    return full_gateway
            raise Exception(f"Gateway '{gateway_name}' exists but could not be found in list")
        else:
            raise e


def create_aws_lambda_target(lambda_arn: str, gatewayID: str, targetname: str):
    """
    Creates an AWS Lambda target and transforms it into MCP tools for use with AgentCore gateway.
    
    Args:
        lambda_arn (str): ARN of the Lambda function to use as the target
        gatewayID (str): ID of the gateway to associate the target with
        targetname (str): Name to give the gateway target
        
    Returns:
        dict: Response from the create_gateway_target API call containing details of the created target
        
    The function:
    1. Configures the Lambda target with tool schemas for get_order and update_order operations
    2. Sets up IAM role-based credentials for the target
    3. Creates the gateway target with the specified configuration
    """

    lambda_target_config = {
        "mcp": {
            "lambda": {
                "lambdaArn": lambda_arn,
                "toolSchema": {
                    "inlinePayload": [
                        {
                            "name": "get_order_tool",
                            "description": "tool to get the order",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "orderId": {
                                        "type": "string"
                                    }
                                },
                                "required": ["orderId"]
                            }
                        },                    
                        {
                            "name": "update_order_tool",
                            "description": "tool to update the orderId",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "orderId": {
                                        "type": "string"
                                    }
                                },
                                "required": ["orderId"]
                            }
                        }
                    ]
                }
            }
        }
    }

    # **credential_config** defines the authentication method for the gateway target
    # Here it specifies that the gateway's IAM role should be used for authentication
    # This means the target will use the permissions granted to the gateway's IAM role
    # when executing Lambda functions
    credential_config = [ 
        {
            "credentialProviderType" : "GATEWAY_IAM_ROLE"
        }
    ]

    try:
        response = gateway_client.create_gateway_target(
            gatewayIdentifier=gatewayID,
            name=targetname,
            description='Lambda Target using SDK',
            targetConfiguration=lambda_target_config,
            credentialProviderConfigurations=credential_config
        )
        return response
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            print(f"Target '{targetname}' already exists. Finding existing target...")
            # List targets to find the existing one
            response = gateway_client.list_gateway_targets(gatewayIdentifier=gatewayID)
            for target in response.get('items', []):
                if target['name'] == targetname:
                    print(f"Found existing target: {target['gatewayTargetId']}")
                    return target
            raise Exception(f"Target '{targetname}' exists but could not be found in list")
        else:
            raise e



def wait_for_gateway_available(gateway_id, max_wait_time=300):
    """
    Wait for gateway to be in AVAILABLE status before proceeding.
    
    Args:
        gateway_id (str): ID of the gateway to check
        max_wait_time (int): Maximum time to wait in seconds
    """
    print(f"Waiting for gateway {gateway_id} to be available...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            response = gateway_client.get_gateway(gatewayIdentifier=gateway_id)
            status = response.get('status')
            print(f"Gateway status: {status}")
            
            if status in ['AVAILABLE', 'READY']:
                print(f"Gateway is now {status.lower()}!")
                return
            elif status in ['FAILED', 'DELETING']:
                raise Exception(f"Gateway creation failed with status: {status}")
                
        except ClientError as e:
            print(f"Error checking gateway status: {e}")
            
        time.sleep(10)
    
    raise Exception(f"Gateway did not become ready within {max_wait_time} seconds")


def main():
    print('(1) Creating Lambda Function')
    lambda_zip = 'lambda_function_code.zip'
    lambda_arn = create_lambda_target(lambda_zip)
    gateway_role_arn = create_gateway_role(role_name = "sample-lambdagateway")

    print("\n(2) Creating Cognito Resources.....")
    cognito_data = create_cognito_resources()

    print('\n(3) Creating AgentCore Gateway.....')
    create_response = create_agentcore_gateway(
        client_id = cognito_data['client_id'],
        cognito_discovery_url = cognito_data['cognito_discovery_url'],
        gateway_name = 'TestGWforLambda',
        gateway_role_arn = gateway_role_arn
    )
    print(json.dumps(create_response, indent=2, default=str))
    gatewayID = create_response["gatewayId"]
    gatewayURL = create_response["gatewayUrl"]
    print(f'Gateway ID: {gatewayID}')

    # Wait for gateway to be available before creating target
    wait_for_gateway_available(gatewayID)

    print('\n(4) Creating Gateway Target.....')
    TARGET_NAME = 'LambdaUsingSDK'
    response = create_aws_lambda_target(lambda_arn, gatewayID, targetname=TARGET_NAME)
    print(json.dumps(response, indent=2, default=str))

    # Save user_pool_id, client_id, client_secret in .env
    with open('.env', 'w') as f:
        f.write(f'USER_POOL_ID={cognito_data["user_pool_id"]}\n')
        f.write(f'CLIENT_ID={cognito_data["client_id"]}\n')
        f.write(f'CLIENT_SECRET={cognito_data["client_secret"]}\n')
        f.write(f'SCOPE_STRING={cognito_data["scopeString"]}\n')
        f.write(f'GATEWAY_URL={gatewayURL}\n')
        f.write(f'TARGET_NAME={TARGET_NAME}\n')

if __name__ == '__main__':
    main()

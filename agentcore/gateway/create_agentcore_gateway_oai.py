import os
import sys
import boto3
from botocore.exceptions import ClientError
from pprint import pprint

# Setup path for agentcore_utils
if '__file__' in globals():
    current_dir = os.path.dirname(os.path.abspath(__file__))
else:
    current_dir = os.getcwd()
sys.path.insert(0, os.path.join(current_dir, '..'))
import agentcore_utils as utils

# Constants
REGION = os.environ.get('AWS_REGION', 'us-west-2')
os.environ['AWS_DEFAULT_REGION'] = REGION

CONFIG = {
    'USER_POOL_NAME': "sample-agentcore-gateway-pool",
    'RESOURCE_SERVER_ID': "sample-agentcore-gateway-id",
    'RESOURCE_SERVER_NAME': "sample-agentcore-gateway-name",
    'CLIENT_NAME': "sample-agentcore-gateway-client",
    'GATEWAY_NAME': 'DemoGWOpenAPIAPIKeyNasaOAI',
    'ROLE_NAME': "sample-lambdagateway",
    'CREDENTIAL_PROVIDER_NAME': "NasaInsightAPIKey",
    'TARGET_NAME': 'DemoOpenAPITargetS3NasaMars',
    'OPENAPI_FILE': 'openapi-specs/nasa_mars_insights_openapi.json',
    'SCOPES': [
        {"ScopeName": "gateway:read", "ScopeDescription": "Read access"},
        {"ScopeName": "gateway:write", "ScopeDescription": "Write access"}
    ]
}

def setup_cognito():
    """Setup Cognito user pool, resource server, and client"""
    cognito = boto3.client("cognito-idp", region_name=REGION)
    
    print("Setting up Cognito resources...")
    user_pool_id = utils.get_or_create_user_pool(cognito, CONFIG['USER_POOL_NAME'])
    utils.get_or_create_resource_server(cognito, user_pool_id, CONFIG['RESOURCE_SERVER_ID'], 
                                      CONFIG['RESOURCE_SERVER_NAME'], CONFIG['SCOPES'])
    client_id, client_secret = utils.get_or_create_m2m_client(cognito, user_pool_id, 
                                                            CONFIG['CLIENT_NAME'], CONFIG['RESOURCE_SERVER_ID'])
    
    discovery_url = f'https://cognito-idp.{REGION}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration'
    
    return client_id, client_secret, discovery_url

def create_gateway(client_id, discovery_url, role_arn):
    """Create AgentCore Gateway"""
    gateway_client = boto3.client('bedrock-agentcore-control', region_name=REGION)
    
    auth_config = {
        "customJWTAuthorizer": {
            "allowedClients": [client_id],
            "discoveryUrl": discovery_url
        }
    }
    
    try:
        response = gateway_client.create_gateway(
            name=CONFIG['GATEWAY_NAME'],
            roleArn=role_arn,
            protocolType='MCP',
            authorizerType='CUSTOM_JWT',
            authorizerConfiguration=auth_config,
            description='AgentCore Gateway with OpenAPI target'
        )
        return response["gatewayId"], response["gatewayUrl"], gateway_client
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            print(f"Gateway already exists: {CONFIG['GATEWAY_NAME']}")
            # Find and return existing gateway
            gateways = gateway_client.list_gateways()['items']
            for gateway in gateways:
                if gateway['name'] == CONFIG['GATEWAY_NAME']:
                    # Get gateway details to retrieve URL
                    gateway_details = gateway_client.get_gateway(gatewayIdentifier=gateway['gatewayId'])
                    return gateway['gatewayId'], gateway_details['gatewayUrl'], gateway_client
        raise

def create_credential_provider(api_key):
    """Create API key credential provider"""
    client = boto3.client("bedrock-agentcore-control")
    
    try:
        response = client.create_api_key_credential_provider(
            name=CONFIG['CREDENTIAL_PROVIDER_NAME'],
            apiKey=api_key
        )
        return response['credentialProviderArn']
    except ClientError as e:
        if e.response['Error']['Code'] == 'ValidationException' and 'already exists' in str(e):
            print(f"Credential provider already exists: {CONFIG['CREDENTIAL_PROVIDER_NAME']}")
            # Generate expected ARN format for existing provider
            sts_client = boto3.client('sts')
            account_id = sts_client.get_caller_identity()['Account']
            return f"arn:aws:bedrock-agentcore:{REGION}:{account_id}:credential-provider/{CONFIG['CREDENTIAL_PROVIDER_NAME']}"
        raise

def upload_openapi_spec():
    """Upload OpenAPI spec to S3"""
    session = boto3.session.Session()
    s3_client = session.client('s3')
    sts_client = session.client('sts')
    
    account_id = sts_client.get_caller_identity()["Account"]
    region = session.region_name
    bucket_name = f'agentcore-gateway-{account_id}-{region}'
    object_key = 'nasa_mars_insights_openapi.json'
    
    # Check if bucket exists
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"S3 bucket already exists: {bucket_name}")
    except ClientError:
        bucket_config = {} if region == "us-east-1" else {'CreateBucketConfiguration': {'LocationConstraint': region}}
        s3_client.create_bucket(Bucket=bucket_name, **bucket_config)
    
    # Check if file exists
    try:
        s3_client.head_object(Bucket=bucket_name, Key=object_key)
        print(f"OpenAPI file already exists in S3: {object_key}")
    except ClientError:
        with open(CONFIG['OPENAPI_FILE'], 'rb') as file_data:
            s3_client.put_object(Bucket=bucket_name, Key=object_key, Body=file_data)
    
    return f's3://{bucket_name}/{object_key}'

def create_gateway_target(gateway_client, gateway_id, s3_uri, credential_arn):
    """Create gateway target with OpenAPI configuration"""
    target_config = {
        "mcp": {
            "openApiSchema": {
                "s3": {"uri": s3_uri}
            }
        }
    }
    
    credential_config = [{
        "credentialProviderType": "API_KEY",
        "credentialProvider": {
            "apiKeyCredentialProvider": {
                "credentialParameterName": "api_key",
                "providerArn": credential_arn,
                "credentialLocation": "QUERY_PARAMETER"
            }
        }
    }]
    
    try:
        return gateway_client.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name=CONFIG['TARGET_NAME'],
            description='OpenAPI Target with S3Uri using SDK',
            targetConfiguration=target_config,
            credentialProviderConfigurations=credential_config
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            print(f"Gateway target already exists: {CONFIG['TARGET_NAME']}")
            # Find and return existing target
            targets = gateway_client.list_gateway_targets(gatewayIdentifier=gateway_id)['items']
            for target in targets:
                if target['name'] == CONFIG['TARGET_NAME']:
                    return target
        raise

def main():
    """Main execution function"""
    api_key = os.environ.get('NASA_API_KEY')
    if not api_key:
        print("Error: NASA_API_KEY environment variable required.")
        print("Usage: NASA_API_KEY=your_key uv run create_gateway_oai.py")
        print("Get API key from: https://api.nasa.gov")
        sys.exit(1)
    
    try:
        # Setup Cognito
        client_id, client_secret, discovery_url = setup_cognito()
        user_pool_id = utils.get_or_create_user_pool(boto3.client("cognito-idp", region_name=REGION), CONFIG['USER_POOL_NAME'])
        print(f"Client ID: {client_id}")
        
        # Get Cognito token
        scope_string = f"{CONFIG['RESOURCE_SERVER_ID']}/gateway:read {CONFIG['RESOURCE_SERVER_ID']}/gateway:write"
        token_response = utils.get_token(user_pool_id, client_id, client_secret, scope_string, REGION)
        token = token_response.get('access_token')
        print(f"Cognito Token: {token}")
        
        # Create IAM role
        role = utils.create_agentcore_gateway_role(CONFIG['ROLE_NAME'])
        role_arn = role['Role']['Arn']
        print(f"Role ARN: {role_arn}")
        
        # Create gateway
        gateway_id, gateway_url, gateway_client = create_gateway(client_id, discovery_url, role_arn)
        print(f"Gateway ID: {gateway_id}")
        
        # Create credential provider
        credential_arn = create_credential_provider(api_key)
        print(f"Credential Provider ARN: {credential_arn}")
        
        # Upload OpenAPI spec
        s3_uri = upload_openapi_spec()
        print(f"OpenAPI S3 URI: {s3_uri}")
        
        # Create gateway target
        target_response = create_gateway_target(gateway_client, gateway_id, s3_uri, credential_arn)
        
        print("\n=== Gateway Setup Complete ===")
        print(f"Gateway URL: {gateway_url}")
        print(f"Gateway ID: {gateway_id}")
        print(f"Target ID: {target_response.get('targetId')}")
        print(f"Access Token: {token}")
        
        # Export environment variables
        os.environ['GATEWAY_URL'] = gateway_url
        os.environ['ACCESS_TOKEN'] = token
        os.environ['TARGET_NAME'] = CONFIG['TARGET_NAME']
        print("\nEnvironment variables exported:")
        print(f"GATEWAY_URL={gateway_url}")
        print(f"ACCESS_TOKEN={token[:20]}...")
        print(f"TARGET_NAME={CONFIG['TARGET_NAME']}")
        
    except ClientError as e:
        print(f"AWS Error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"OpenAPI file not found: {CONFIG['OPENAPI_FILE']}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
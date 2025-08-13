#!/usr/bin/env python

# This code has been adapted from:
# https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/02-AgentCore-gateway/01-transform-lambda-into-mcp-tools/01-gateway-target-lambda.ipynb

import os
import utils

from dotenv import load_dotenv

load_dotenv()

REGION = os.getenv('AWS_REGION', 'us-west-2')
USER_POOL_ID = os.getenv('USER_POOL_ID')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
SCOPE_STRING = os.getenv('SCOPE_STRING')


def get_cognito_token(user_pool_id, client_id, client_secret, scopeString):
    """
    Retrieves an access token from Amazon Cognito for authorization.
    
    Args:
        user_pool_id (str): ID of the Cognito user pool
        client_id (str): ID of the client
        client_secret (str): Secret for the client
        scopeString (str): Scopes for the token
        REGION (str): AWS region
        
    Returns:
        dict: Token response containing the access token
    """

    print("Requesting the access token from Amazon Cognito authorizer...")
    token_response = utils.get_token(user_pool_id, client_id, client_secret, scopeString, REGION)
    return token_response["access_token"]


def main():
    cognito_token = get_cognito_token(
        user_pool_id = USER_POOL_ID,
        client_id = CLIENT_ID,
        client_secret = CLIENT_SECRET,
        scopeString = SCOPE_STRING
    )
    print("Token response:", cognito_token)


if __name__ == "__main__":
    main()

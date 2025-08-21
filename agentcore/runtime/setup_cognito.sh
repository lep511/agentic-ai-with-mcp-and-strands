#!/bin/bash

# This script has been adapted from:
# https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html

if [ "$AWS_REGION" = "" ]; then
    AWS_REGION="us-west-2"
fi
echo "Using region $AWS_REGION"

# Create User Pool and capture Pool ID directly
export POOL_ID=$(aws cognito-idp create-user-pool \
  --pool-name "MyUserPool" \
  --policies '{"PasswordPolicy":{"MinimumLength":8}}' \
  --region $AWS_REGION | jq -r '.UserPool.Id')
echo "Pool id: $POOL_ID"

# Create App Client and capture Client ID directly
export CLIENT_ID=$(aws cognito-idp create-user-pool-client \
  --user-pool-id $POOL_ID \
  --client-name "MyClient" \
  --no-generate-secret \
  --explicit-auth-flows "ALLOW_USER_PASSWORD_AUTH" "ALLOW_REFRESH_TOKEN_AUTH" \
  --region $AWS_REGION | jq -r '.UserPoolClient.ClientId')
echo "Client ID: $CLIENT_ID"

# Create User
aws cognito-idp admin-create-user \
  --user-pool-id $POOL_ID \
  --username "testuser" \
  --temporary-password "TEMP_PASSWORD" \
  --region $AWS_REGION \
  --message-action SUPPRESS > /dev/null
echo "Cognito user created"

# Set Permanent Password
aws cognito-idp admin-set-user-password \
  --user-pool-id $POOL_ID \
  --username "testuser" \
  --password "PERMANENT_PASSWORD" \
  --region $AWS_REGION \
  --permanent > /dev/null
echo "Cognito user password set"

# Save the variables POOL_ID, Discovery URL, CLIENT_ID, and BEARER_TOKEN in `.env`
cat << EOF > .env
POOL_ID=$POOL_ID
DISCOVERY_URL=https://cognito-idp.$AWS_REGION.amazonaws.com/$POOL_ID/.well-known/openid-configuration
CLIENT_ID=$CLIENT_ID
EOF

# Output the required values
echo "----- Environment variables saved in .env -----"
cat .env

import os
from bedrock_agentcore.services.identity import IdentityClient

api_key = os.getenv("OPENAI_API_KEY", "")
aws_region = os.getenv("AWS_REGION", "us-west-2")


identity_client = IdentityClient(region=aws_region)

api_key_provider = identity_client.create_api_key_credential_provider({
    "name": "openai-apikey-provider",
    "apiKey": api_key
})
print(api_key_provider)
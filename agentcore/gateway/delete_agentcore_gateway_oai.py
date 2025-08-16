#!/usr/bin/env python3
import os
import sys
import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get('AWS_REGION', 'us-west-2')

def delete_gateway():
    gateway_id = os.environ.get('GATEWAY_ID')
    if not gateway_id:
        print("Error: GATEWAY_ID environment variable required.")
        sys.exit(1)
    
    client = boto3.client('bedrock-agentcore-control', region_name=REGION)
    
    try:
        list_response = client.list_gateway_targets(
          gatewayIdentifier = gateway_id,
          maxResults=100
        )
        for item in list_response['items']:
          target_id = item["targetId"]
          print("Deleting target ", target_id)
          client.delete_gateway_target(
            gatewayIdentifier = gateway_id,
            targetId = target_id
          )
        print("Deleting gateway ", gateway_id)
        client.delete_gateway(gatewayIdentifier=gateway_id)
        print(f"Gateway {gateway_id} deleted successfully")
    except ClientError as e:
        print(f"Error deleting gateway: {e}")
        sys.exit(1)

if __name__ == "__main__":
    delete_gateway()
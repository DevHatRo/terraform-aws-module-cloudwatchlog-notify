#!/usr/bin/env python3
"""
Script to generate a CloudWatch Logs test event and invoke a Lambda function.
"""
import base64
import boto3
import gzip
import json
import os
import sys
import time
from botocore.exceptions import ClientError

def invoke_lambda(function_name="cloudwatch-notifier", endpoint_url=None, max_retries=10, retry_delay=3):
    """
    Create a test CloudWatch Logs event and invoke the Lambda function.
    
    Args:
        function_name (str): Name of the Lambda function to invoke
        endpoint_url (str): Optional endpoint URL for LocalStack
        max_retries (int): Maximum number of retries
        retry_delay (int): Delay between retries in seconds
    """
    # Create log data structure with Kubernetes log format
    log_data = {
        "messageType": "DATA_MESSAGE",
        "owner": "123456789012",
        "logGroup": "/aws/lambda/test-function",
        "logStream": "2024/01/01/[$LATEST]1234567890",
        "subscriptionFilters": ["filter"],
        "logEvents": [
            {
                "id": "event1",
                "timestamp": 1699999999000,
                "message": json.dumps({
                    "log": "test error",
                    "kubernetes": {
                        "pod_name": "test-pod",
                        "namespace_name": "test-namespace",
                        "container_name": "test-app"
                    }
                })
            }
        ]
    }

    # Compress and encode the log data
    compressed_data = gzip.compress(json.dumps(log_data).encode("utf-8"))
    encoded_data = base64.b64encode(compressed_data).decode("utf-8")
    
    # Create the final event structure
    event = {
        "awslogs": {
            "data": encoded_data
        }
    }
    
    # Convert to JSON string
    payload = json.dumps(event)
    
    # Configure boto3 client
    lambda_kwargs = {}
    if endpoint_url:
        lambda_kwargs['endpoint_url'] = endpoint_url
    
    # Get endpoint from environment variable if not provided
    if not endpoint_url and 'AWS_ENDPOINT_URL' in os.environ:
        lambda_kwargs['endpoint_url'] = os.environ['AWS_ENDPOINT_URL']
    
    # Create Lambda client
    lambda_client = boto3.client('lambda', **lambda_kwargs)
    
    # Try to invoke Lambda function with retries
    retries = 0
    while retries < max_retries:
        try:
            print(f"Invoking Lambda function {function_name} with CloudWatch Logs test event (attempt {retries+1}/{max_retries})...")
            
            # Wait for Lambda function to be active
            if retries > 0:
                try:
                    # Check function status first
                    get_response = lambda_client.get_function(FunctionName=function_name)
                    config = get_response.get('Configuration', {})
                    state = config.get('State')
                    print(f"Lambda function state: {state}")
                    
                    if state == 'Pending':
                        print(f"Function still initializing. Waiting {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retries += 1
                        continue
                except Exception as e:
                    print(f"Error checking function status: {str(e)}")
            
            # Invoke the function
            response = lambda_client.invoke(
                FunctionName=function_name,
                Payload=payload.encode('utf-8')
            )
            
            # Process response
            status_code = response.get('StatusCode')
            print(f"Lambda invocation status code: {status_code}")
            
            # Get and decode payload from response
            result_payload = response.get('Payload')
            if result_payload:
                result = result_payload.read().decode('utf-8')
                print(f"Lambda response: {result}")
                
                # Save response to output.json for compatibility with existing workflow
                with open('output.json', 'w') as f:
                    f.write(result)
                print("Response saved to output.json")
            
            return status_code
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            error_message = e.response.get('Error', {}).get('Message')
            
            if error_code == 'ResourceConflictException' and 'Pending' in error_message:
                print(f"Function still initializing. Waiting {retry_delay} seconds... ({error_message})")
                time.sleep(retry_delay)
                retries += 1
            else:
                # Unexpected error
                print(f"Error invoking Lambda: {str(e)}")
                raise
    
    raise Exception(f"Failed to invoke Lambda function after {max_retries} attempts")

if __name__ == "__main__":
    # Get function name from command line argument if provided
    function_name = sys.argv[1] if len(sys.argv) > 1 else "cloudwatch-notifier"
    
    # Get endpoint URL from command line argument if provided
    endpoint_url = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        # Invoke the Lambda function
        status_code = invoke_lambda(function_name, endpoint_url)
        
        # Exit with appropriate status code
        if status_code >= 200 and status_code < 300:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1) 

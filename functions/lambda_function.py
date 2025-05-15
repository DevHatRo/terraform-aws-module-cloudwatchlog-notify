import base64
import gzip
import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize boto3 client
sns_client = boto3.client('sns')

def lambda_handler(event, context):
    """
    Main Lambda handler function for processing CloudWatch Logs events
    and forwarding them to SNS.
    """
    logger.info("Event received: %s", json.dumps(event))
    
    # Get SNS ARN from environment variable
    sns_arn = os.environ.get('SNS_ARN')
    if not sns_arn:
        logger.error("SNS_ARN environment variable not set")
        return {
            'statusCode': 500,
            'body': json.dumps('SNS_ARN environment variable not set')
        }
    
    # Check if this is an SNS event
    if 'Records' in event:
        for record in event['Records']:
            if record.get('EventSource') == 'aws:sns' or record.get('eventSource') == 'aws:sns':
                logger.info("Processing SNS message")
                sns_message = record.get('Sns', {}).get('Message')
                if sns_message:
                    try:
                        sns_data = json.loads(sns_message)
                        process_cloudwatch_log_event(sns_data, sns_arn)
                    except json.JSONDecodeError:
                        logger.error("Failed to parse SNS message as JSON: %s", sns_message)
                        return {
                            'statusCode': 400,
                            'body': json.dumps('Invalid SNS message format')
                        }
    # Check if this is a direct CloudWatch Logs event
    elif 'awslogs' in event:
        process_cloudwatch_log_event(event, sns_arn)
    else:
        logger.error("Unknown event format: %s", json.dumps(event))
        return {
            'statusCode': 400,
            'body': json.dumps('Unknown event format')
        }
    
    return {
        'statusCode': 200,
        'body': json.dumps('Successfully processed CloudWatch Logs')
    }

def process_cloudwatch_log_event(event, sns_arn):
    """
    Process a CloudWatch Logs event and forward to SNS.
    
    Args:
        event (dict): CloudWatch Logs event data
        sns_arn (str): SNS topic ARN to send notifications to
    """
    # Extract the compressed log data
    compressed_data = event.get('awslogs', {}).get('data', '')
    if not compressed_data:
        logger.warning("No log data found in event")
        return
    
    # Decompress the log data
    try:
        compressed_bytes = base64.b64decode(compressed_data)
        uncompressed_bytes = gzip.decompress(compressed_bytes)
        log_data = json.loads(uncompressed_bytes)
        logger.info("Decoded log data: %s", json.dumps(log_data))
    except Exception as e:
        logger.error("Failed to decode log data: %s", str(e))
        return
    
    # Check if there are any log events
    log_events = log_data.get('logEvents', [])
    if not log_events:
        logger.info("No log events found")
        return
    
    # Process each log event
    for log_event in log_events:
        try:
            # Extract basic information
            log_group = log_data.get('logGroup', 'unknown')
            log_stream = log_data.get('logStream', 'unknown')
            message = log_event.get('message', '')
            
            # Try to parse message as JSON if possible
            try:
                message_json = json.loads(message)
                # Format k8s logs specially if they contain kubernetes metadata
                if isinstance(message_json, dict) and 'kubernetes' in message_json:
                    k8s = message_json.get('kubernetes', {})
                    namespace = k8s.get('namespace_name', 'unknown')
                    pod = k8s.get('pod_name', 'unknown')
                    container = k8s.get('container_name', 'unknown')
                    log_content = message_json.get('log', message)
                    
                    notification_message = (
                        f"Error detected in Kubernetes logs:\n\n"
                        f"Namespace: {namespace}\n"
                        f"Pod: {pod}\n"
                        f"Container: {container}\n"
                        f"Log Group: {log_group}\n"
                        f"Log Stream: {log_stream}\n\n"
                        f"Message: {log_content}"
                    )
                else:
                    notification_message = (
                        f"Error detected in logs:\n\n"
                        f"Log Group: {log_group}\n"
                        f"Log Stream: {log_stream}\n\n"
                        f"Message: {json.dumps(message_json, indent=2)}"
                    )
            except json.JSONDecodeError:
                # Not JSON, use raw message
                notification_message = (
                    f"Error detected in logs:\n\n"
                    f"Log Group: {log_group}\n"
                    f"Log Stream: {log_stream}\n\n"
                    f"Message: {message}"
                )
            
            # Send to SNS
            send_to_sns(notification_message, sns_arn)
            
        except Exception as e:
            logger.error("Error processing log event: %s", str(e))

def send_to_sns(message, sns_arn):
    """
    Send a message to an SNS topic.
    
    Args:
        message (str): Message to send
        sns_arn (str): SNS topic ARN
    """
    try:
        response = sns_client.publish(
            TopicArn=sns_arn,
            Message=message,
            Subject="CloudWatch Logs Alert"
        )
        logger.info("Message sent to SNS: %s", response['MessageId'])
    except ClientError as e:
        logger.error("Failed to send message to SNS: %s", str(e)) 

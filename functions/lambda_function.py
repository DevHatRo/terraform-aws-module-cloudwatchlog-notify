import base64
import gzip
import json
import logging
import os
import urllib.request

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
                        # Try to parse the message as JSON
                        sns_data = json.loads(sns_message)
                        
                        # Check if this is a CloudWatch Alarm
                        if 'AlarmName' in sns_data:
                            logger.info("Processing CloudWatch Alarm notification")
                            process_cloudwatch_alarm(sns_data, sns_arn)
                        # If it has awslogs data, it's a CloudWatch Logs event
                        elif 'awslogs' in sns_data:
                            logger.info("Processing CloudWatch Logs notification from SNS")
                            process_cloudwatch_log_event(sns_data, sns_arn)
                        else:
                            logger.info("Processing generic SNS notification")
                            process_generic_sns_message(sns_data, sns_arn)
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

def process_cloudwatch_alarm(alarm_data, sns_arn):
    """
    Process CloudWatch Alarm data and forward to SNS/Slack.

    Args:
        alarm_data (dict): CloudWatch Alarm data
        sns_arn (str): SNS topic ARN to send notifications to
    """
    try:
        # Extract basic alarm information
        alarm_name = alarm_data.get('AlarmName', 'Unknown Alarm')
        alarm_description = alarm_data.get('AlarmDescription', 'No description')
        alarm_reason = alarm_data.get('NewStateReason', 'No reason provided')
        alarm_state = alarm_data.get('NewStateValue', 'UNKNOWN')
        region = alarm_data.get('Region', 'unknown-region')
        
        # Create notification message for email
        notification_message = (
            f"CloudWatch Alarm: {alarm_name}\n\n"
            f"State: {alarm_state}\n"
            f"Description: {alarm_description}\n"
            f"Region: {region}\n\n"
            f"Reason: {alarm_reason}\n\n"
            f"Details: {json.dumps(alarm_data, indent=2)}"
        )

        # Create Slack message
        color = "danger" if alarm_state == "ALARM" else "good" if alarm_state == "OK" else "warning"
        slack_message = {
            "attachments": [{
                "color": color,
                "title": f"CloudWatch Alarm: {alarm_name}",
                "fields": [
                    {"title": "State", "value": alarm_state, "short": True},
                    {"title": "Region", "value": region, "short": True},
                    {"title": "Description", "value": alarm_description, "short": False},
                    {"title": "Reason", "value": alarm_reason, "short": False}
                ]
            }]
        }

        # Send to SNS
        send_to_sns(notification_message, sns_arn)

        # Send to Slack if enabled
        if os.environ.get('ENABLE_SLACK', 'false').lower() == 'true':
            slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
            if slack_webhook_url:
                # Add channel if specified
                slack_channel = os.environ.get('SLACK_CHANNEL')
                if slack_channel:
                    slack_message['channel'] = slack_channel
                
                # Add username if specified
                slack_username = os.environ.get('SLACK_USERNAME')
                if slack_username:
                    slack_message['username'] = slack_username
                
                send_to_slack(slack_message, slack_webhook_url)

    except Exception as e:
        logger.error("Error processing CloudWatch Alarm: %s", str(e))

def process_generic_sns_message(sns_data, sns_arn):
    """
    Process a generic SNS message and forward it.

    Args:
        sns_data (dict): The SNS message data
        sns_arn (str): SNS topic ARN to send notifications to
    """
    try:
        # Create a simple message from the data
        notification_message = f"SNS Notification:\n\n{json.dumps(sns_data, indent=2)}"
        
        # Create Slack message
        slack_message = {
            "attachments": [{
                "color": "good",
                "title": "SNS Notification",
                "text": json.dumps(sns_data, indent=2)
            }]
        }

        # Send to SNS
        send_to_sns(notification_message, sns_arn)

        # Send to Slack if enabled
        if os.environ.get('ENABLE_SLACK', 'false').lower() == 'true':
            slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
            if slack_webhook_url:
                # Add channel if specified
                slack_channel = os.environ.get('SLACK_CHANNEL')
                if slack_channel:
                    slack_message['channel'] = slack_channel
                
                # Add username if specified
                slack_username = os.environ.get('SLACK_USERNAME')
                if slack_username:
                    slack_message['username'] = slack_username
                
                send_to_slack(slack_message, slack_webhook_url)
    
    except Exception as e:
        logger.error("Error processing generic SNS message: %s", str(e))

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

                    slack_message = {
                        "attachments": [{
                            "color": "danger",
                            "title": f"Error in Kubernetes: {namespace}/{pod}",
                            "fields": [
                                {"title": "Namespace", "value": namespace, "short": True},
                                {"title": "Pod", "value": pod, "short": True},
                                {"title": "Container", "value": container, "short": True},
                                {"title": "Log Group", "value": log_group, "short": True},
                                {"title": "Log Stream", "value": log_stream, "short": True},
                                {"title": "Message", "value": log_content, "short": False}
                            ]
                        }]
                    }
                else:
                    notification_message = (
                        f"Error detected in logs:\n\n"
                        f"Log Group: {log_group}\n"
                        f"Log Stream: {log_stream}\n\n"
                        f"Message: {json.dumps(message_json, indent=2)}"
                    )

                    slack_message = {
                        "attachments": [{
                            "color": "danger",
                            "title": f"Error in {log_group}",
                            "fields": [
                                {"title": "Log Group", "value": log_group, "short": True},
                                {"title": "Log Stream", "value": log_stream, "short": True},
                                {"title": "Message", "value": json.dumps(message_json, indent=2), "short": False}
                            ]
                        }]
                    }
            except json.JSONDecodeError:
                # Not JSON, use raw message
                notification_message = (
                    f"Error detected in logs:\n\n"
                    f"Log Group: {log_group}\n"
                    f"Log Stream: {log_stream}\n\n"
                    f"Message: {message}"
                )

                slack_message = {
                    "attachments": [{
                        "color": "danger",
                        "title": f"Error in {log_group}",
                        "fields": [
                            {"title": "Log Group", "value": log_group, "short": True},
                            {"title": "Log Stream", "value": log_stream, "short": True},
                            {"title": "Message", "value": message, "short": False}
                        ]
                    }]
                }

            # Send to SNS
            send_to_sns(notification_message, sns_arn)

            # Send to Slack if enabled
            if os.environ.get('ENABLE_SLACK', 'false').lower() == 'true':
                slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
                if slack_webhook_url:
                    # Add channel if specified
                    slack_channel = os.environ.get('SLACK_CHANNEL')
                    if slack_channel:
                        slack_message['channel'] = slack_channel
                    
                    # Add username if specified
                    slack_username = os.environ.get('SLACK_USERNAME')
                    if slack_username:
                        slack_message['username'] = slack_username
                    
                    send_to_slack(slack_message, slack_webhook_url)

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
        # Get email subject from environment variable with fallback
        email_subject = os.environ.get('EMAIL_SUBJECT', 'CloudWatch Alert')
        
        response = sns_client.publish(
            TopicArn=sns_arn,
            Message=message,
            Subject=email_subject
        )
        logger.info("Message sent to SNS: %s", response['MessageId'])
    except ClientError as e:
        logger.error("Failed to send message to SNS: %s", str(e))

def send_to_slack(message, webhook_url):
    """
    Send a message to a Slack webhook.

    Args:
        message (dict): Slack-formatted message to send
        webhook_url (str): Slack webhook URL
    """
    try:
        data = json.dumps(message).encode('utf-8')
        headers = {'Content-Type': 'application/json'}
        req = urllib.request.Request(webhook_url, data=data, headers=headers)
        
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                logger.error("Failed to send message to Slack. Status code: %s", response.status)
            else:
                logger.info("Message sent to Slack successfully")
    except Exception as e:
        logger.error("Error sending message to Slack: %s", str(e))

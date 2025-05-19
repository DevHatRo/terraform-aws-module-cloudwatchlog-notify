import base64
import gzip
import json
import os
import unittest
from unittest.mock import patch, MagicMock

import lambda_function


class TestLambdaFunction(unittest.TestCase):
    """Test cases for the CloudWatch Logs Notifier Lambda function"""

    def setUp(self):
        """Set up test fixtures"""
        # Set environment variables
        os.environ['SNS_ARN'] = 'arn:aws:sns:us-east-1:123456789012:test-topic'

    def tearDown(self):
        """Tear down test fixtures"""
        # Remove environment variables
        if 'SNS_ARN' in os.environ:
            del os.environ['SNS_ARN']

    def create_test_cw_logs_event(self, message):
        """Create a test CloudWatch Logs event with the given message"""
        # Create a log object with the test message
        log_event = {
            "id": "12345678901234",
            "timestamp": 1607456000000,
            "message": message
        }

        # Create the CloudWatch Logs data
        log_data = {
            "messageType": "DATA_MESSAGE",
            "owner": "123456789012",
            "logGroup": "/aws/lambda/test-function",
            "logStream": "test-stream",
            "subscriptionFilters": ["test-filter"],
            "logEvents": [log_event]
        }

        # Compress and encode the log data
        compressed_data = gzip.compress(json.dumps(log_data).encode('utf-8'))
        encoded_data = base64.b64encode(compressed_data).decode('utf-8')

        # Return the CloudWatch Logs event
        return {
            "awslogs": {
                "data": encoded_data
            }
        }

    @patch('lambda_function.sns_client')
    def test_lambda_handler_regular_log(self, mock_sns_client):
        """Test handling a regular log message"""
        # Create a test event with a regular log message
        event = self.create_test_cw_logs_event("This is a test error message")

        # Mock the SNS publish response
        mock_sns_client.publish.return_value = {'MessageId': 'test-message-id'}

        # Call the Lambda handler
        result = lambda_function.lambda_handler(event, {})

        # Check if SNS publish was called
        mock_sns_client.publish.assert_called_once()

        # Check the response
        self.assertEqual(result['statusCode'], 200)
        self.assertEqual(json.loads(result['body']), 'Successfully processed CloudWatch Logs')

    @patch('lambda_function.sns_client')
    def test_lambda_handler_json_log(self, mock_sns_client):
        """Test handling a JSON log message"""
        # Create a test event with a JSON log message
        json_message = json.dumps({
            "level": "ERROR",
            "message": "Test error",
            "details": {"key": "value"}
        })
        event = self.create_test_cw_logs_event(json_message)

        # Mock the SNS publish response
        mock_sns_client.publish.return_value = {'MessageId': 'test-message-id'}

        # Call the Lambda handler
        result = lambda_function.lambda_handler(event, {})

        # Check if SNS publish was called
        mock_sns_client.publish.assert_called_once()

        # Check the response
        self.assertEqual(result['statusCode'], 200)
        self.assertEqual(json.loads(result['body']), 'Successfully processed CloudWatch Logs')

    @patch('lambda_function.sns_client')
    def test_lambda_handler_kubernetes_log(self, mock_sns_client):
        """Test handling a Kubernetes log message"""
        # Create a test event with a Kubernetes log message
        k8s_message = json.dumps({
            "kubernetes": {
                "namespace_name": "test-namespace",
                "pod_name": "test-pod",
                "container_name": "test-container"
            },
            "log": "Test error in Kubernetes",
            "level": "ERROR"
        })
        event = self.create_test_cw_logs_event(k8s_message)

        # Mock the SNS publish response
        mock_sns_client.publish.return_value = {'MessageId': 'test-message-id'}

        # Call the Lambda handler
        result = lambda_function.lambda_handler(event, {})

        # Check if SNS publish was called
        mock_sns_client.publish.assert_called_once()

        # Check the response
        self.assertEqual(result['statusCode'], 200)
        self.assertEqual(json.loads(result['body']), 'Successfully processed CloudWatch Logs')

    @patch('lambda_function.sns_client')
    def test_lambda_handler_no_sns_arn(self, mock_sns_client):
        """Test handling when SNS_ARN is not set"""
        # Remove the SNS_ARN environment variable
        if 'SNS_ARN' in os.environ:
            del os.environ['SNS_ARN']

        # Create a test event
        event = self.create_test_cw_logs_event("This is a test error message")

        # Call the Lambda handler
        result = lambda_function.lambda_handler(event, {})

        # Check the response
        self.assertEqual(result['statusCode'], 500)
        self.assertEqual(json.loads(result['body']), 'SNS_ARN environment variable not set')

        # Check that SNS publish was not called
        mock_sns_client.publish.assert_not_called()

    @patch('lambda_function.sns_client')
    def test_lambda_handler_sns_event(self, mock_sns_client):
        """Test handling an SNS event with a CloudWatch Logs payload"""
        # Create a CloudWatch Logs event
        cw_logs_event = self.create_test_cw_logs_event("This is a test error message")

        # Wrap it in an SNS message
        sns_message = json.dumps(cw_logs_event)

        # Create an SNS event that would be received from SNS subscription
        event = {
            "Records": [
                {
                    "EventSource": "aws:sns",
                    "EventVersion": "1.0",
                    "EventSubscriptionArn": "arn:aws:sns:us-east-1:123456789012:test-topic:subscription-id",
                    "Sns": {
                        "Type": "Notification",
                        "MessageId": "12345678-1234-1234-1234-123456789012",
                        "TopicArn": "arn:aws:sns:us-east-1:123456789012:test-topic",
                        "Subject": "Test Subject",
                        "Message": sns_message,
                        "Timestamp": "2023-01-01T00:00:00.000Z",
                        "SignatureVersion": "1",
                        "Signature": "test-signature",
                        "SigningCertUrl": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-12345.pem",
                        "UnsubscribeUrl": "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:123456789012:test-topic:subscription-id",
                        "MessageAttributes": {}
                    }
                }
            ]
        }

        # Mock the SNS publish response
        mock_sns_client.publish.return_value = {'MessageId': 'test-message-id'}

        # Call the Lambda handler
        result = lambda_function.lambda_handler(event, {})

        # Check if SNS publish was called
        mock_sns_client.publish.assert_called_once()

        # Check the response
        self.assertEqual(result['statusCode'], 200)
        self.assertEqual(json.loads(result['body']), 'Successfully processed CloudWatch Logs')

    @patch('lambda_function.sns_client')
    def test_lambda_handler_sns_event_invalid_json(self, mock_sns_client):
        """Test handling an SNS event with invalid JSON message"""
        # Create an SNS event with invalid JSON in the message
        event = {
            "Records": [
                {
                    "EventSource": "aws:sns",
                    "EventVersion": "1.0",
                    "EventSubscriptionArn": "arn:aws:sns:us-east-1:123456789012:test-topic:subscription-id",
                    "Sns": {
                        "Type": "Notification",
                        "MessageId": "12345678-1234-1234-1234-123456789012",
                        "TopicArn": "arn:aws:sns:us-east-1:123456789012:test-topic",
                        "Subject": "Test Subject",
                        "Message": "{invalid json",  # Invalid JSON
                        "Timestamp": "2023-01-01T00:00:00.000Z",
                        "SignatureVersion": "1",
                        "Signature": "test-signature",
                        "SigningCertUrl": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-12345.pem",
                        "UnsubscribeUrl": "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:123456789012:test-topic:subscription-id",
                        "MessageAttributes": {}
                    }
                }
            ]
        }

        # Call the Lambda handler
        result = lambda_function.lambda_handler(event, {})

        # Check that SNS publish was not called (error case)
        mock_sns_client.publish.assert_not_called()

        # Check the response has error status code
        self.assertEqual(result['statusCode'], 400)
        self.assertEqual(json.loads(result['body']), 'Invalid SNS message format')

    @patch('lambda_function.sns_client')
    def test_lambda_handler_unknown_event(self, mock_sns_client):
        """Test handling an unknown event format"""
        # Create an event with an unknown format
        event = {
            "some_key": "some_value"
        }

        # Call the Lambda handler
        result = lambda_function.lambda_handler(event, {})

        # Check the response
        self.assertEqual(result['statusCode'], 400)
        self.assertEqual(json.loads(result['body']), 'Unknown event format')

        # Check that SNS publish was not called
        mock_sns_client.publish.assert_not_called()

    @patch('lambda_function.sns_client')
    @patch('lambda_function.urllib.request.Request')
    @patch('lambda_function.urllib.request.urlopen')
    def test_slack_notification_enabled(self, mock_urlopen, mock_request, mock_sns_client):
        """Test sending notifications to Slack when enabled"""
        # Set environment variables for Slack
        os.environ['ENABLE_SLACK'] = 'true'
        os.environ['SLACK_WEBHOOK_URL'] = 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'
        os.environ['SLACK_CHANNEL'] = '#test-channel'
        os.environ['SLACK_USERNAME'] = 'CloudWatch-Bot'

        # Configure mocks
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        mock_sns_client.publish.return_value = {'MessageId': 'test-message-id'}

        # Create a test event with a regular log message
        event = self.create_test_cw_logs_event("This is a test error message")

        # Call the Lambda handler
        result = lambda_function.lambda_handler(event, {})

        # Check if SNS publish was called
        mock_sns_client.publish.assert_called_once()

        # Check if Slack webhook was called
        mock_request.assert_called_once()
        mock_urlopen.assert_called_once()

        # Get the actual call arguments
        call_args = mock_request.call_args
        actual_data = json.loads(call_args[1]['data'].decode('utf-8'))

        # Verify the structure of the Slack message
        self.assertEqual(actual_data['channel'], '#test-channel')
        self.assertEqual(actual_data['username'], 'CloudWatch-Bot')
        self.assertTrue('attachments' in actual_data)

        # Verify the attachment structure
        attachment = actual_data['attachments'][0]
        self.assertEqual(attachment['color'], 'danger')
        self.assertEqual(attachment['title'], 'Error in /aws/lambda/test-function')

        # Verify the fields
        fields = attachment['fields']
        self.assertEqual(len(fields), 3)
        self.assertEqual(fields[0]['title'], 'Log Group')
        self.assertEqual(fields[0]['value'], '/aws/lambda/test-function')
        self.assertEqual(fields[1]['title'], 'Log Stream')
        self.assertEqual(fields[1]['value'], 'test-stream')
        self.assertEqual(fields[2]['title'], 'Message')
        self.assertEqual(fields[2]['value'], 'This is a test error message')

        # Check the response
        self.assertEqual(result['statusCode'], 200)
        self.assertEqual(json.loads(result['body']), 'Successfully processed CloudWatch Logs')

        # Clean up
        del os.environ['ENABLE_SLACK']
        del os.environ['SLACK_WEBHOOK_URL']
        del os.environ['SLACK_CHANNEL']
        del os.environ['SLACK_USERNAME']

    @patch('lambda_function.sns_client')
    @patch('lambda_function.urllib.request.Request')
    @patch('lambda_function.urllib.request.urlopen')
    def test_slack_notification_disabled(self, mock_urlopen, mock_request, mock_sns_client):
        """Test that Slack notifications are not sent when disabled"""
        # Set environment variables for Slack (disabled)
        os.environ['ENABLE_SLACK'] = 'false'
        os.environ['SLACK_WEBHOOK_URL'] = 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'

        # Configure mocks
        mock_sns_client.publish.return_value = {'MessageId': 'test-message-id'}

        # Create a test event with a regular log message
        event = self.create_test_cw_logs_event("This is a test error message")

        # Call the Lambda handler
        result = lambda_function.lambda_handler(event, {})

        # Check if SNS publish was called
        mock_sns_client.publish.assert_called_once()

        # Check that urllib.request was not used (no Slack call)
        mock_urlopen.assert_not_called()

        # Check the response
        self.assertEqual(result['statusCode'], 200)
        self.assertEqual(json.loads(result['body']), 'Successfully processed CloudWatch Logs')

        # Clean up
        del os.environ['ENABLE_SLACK']
        del os.environ['SLACK_WEBHOOK_URL']

    @patch('lambda_function.sns_client')
    @patch('lambda_function.urllib.request.Request')
    @patch('lambda_function.urllib.request.urlopen')
    def test_slack_error_handling(self, mock_urlopen, mock_request, mock_sns_client):
        """Test handling errors during Slack notification"""
        # Set environment variables for Slack
        os.environ['ENABLE_SLACK'] = 'true'
        os.environ['SLACK_WEBHOOK_URL'] = 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'

        # Configure mocks
        mock_response = MagicMock()
        mock_response.status = 400  # Error status
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        mock_sns_client.publish.return_value = {'MessageId': 'test-message-id'}

        # Create a test event with a regular log message
        event = self.create_test_cw_logs_event("This is a test error message")

        # Call the Lambda handler
        result = lambda_function.lambda_handler(event, {})

        # Check if SNS publish was called
        mock_sns_client.publish.assert_called_once()

        # Check if Slack webhook was called
        mock_request.assert_called_once()
        mock_urlopen.assert_called_once()

        # Check the response (should still be 200 despite Slack error)
        self.assertEqual(result['statusCode'], 200)
        self.assertEqual(json.loads(result['body']), 'Successfully processed CloudWatch Logs')

        # Clean up
        del os.environ['ENABLE_SLACK']
        del os.environ['SLACK_WEBHOOK_URL']

    @patch('lambda_function.sns_client')
    def test_lambda_handler_cloudwatch_alarm(self, mock_sns_client):
        """Test handling a CloudWatch Alarm event"""
        # Create a CloudWatch Alarm message
        cloudwatch_alarm = {
            "AlarmName": "test-alarm",
            "AlarmDescription": "This is a test alarm",
            "AWSAccountId": "123456789012",
            "NewStateValue": "ALARM",
            "NewStateReason": "Threshold Crossed",
            "StateChangeTime": "2023-01-01T00:00:00.000+0000",
            "Region": "us-east-1",
            "OldStateValue": "OK",
            "Trigger": {
                "MetricName": "CPUUtilization",
                "Namespace": "AWS/EC2",
                "StatisticType": "Statistic",
                "Statistic": "AVERAGE",
                "Unit": None,
                "Dimensions": [],
                "Period": 300,
                "EvaluationPeriods": 1,
                "ComparisonOperator": "GreaterThanThreshold",
                "Threshold": 80.0
            }
        }

        # Wrap it in an SNS event
        sns_message = json.dumps(cloudwatch_alarm)
        event = {
            "Records": [
                {
                    "EventSource": "aws:sns",
                    "EventVersion": "1.0",
                    "EventSubscriptionArn": "arn:aws:sns:us-east-1:123456789012:test-topic:subscription-id",
                    "Sns": {
                        "Type": "Notification",
                        "MessageId": "12345678-1234-1234-1234-123456789012",
                        "TopicArn": "arn:aws:sns:us-east-1:123456789012:test-topic",
                        "Subject": "Test Subject",
                        "Message": sns_message,
                        "Timestamp": "2023-01-01T00:00:00.000Z",
                        "SignatureVersion": "1",
                        "Signature": "test-signature",
                        "SigningCertUrl": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-12345.pem",
                        "UnsubscribeUrl": "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:123456789012:test-topic:subscription-id",
                        "MessageAttributes": {}
                    }
                }
            ]
        }

        # Mock the SNS publish response
        mock_sns_client.publish.return_value = {'MessageId': 'test-message-id'}

        # Call the Lambda handler
        result = lambda_function.lambda_handler(event, {})

        # Check if SNS publish was called
        mock_sns_client.publish.assert_called_once()

        # Verify the correct subject was used
        self.assertEqual(mock_sns_client.publish.call_args[1]['Subject'], 'CloudWatch Alert')

        # Check the response
        self.assertEqual(result['statusCode'], 200)
        self.assertEqual(json.loads(result['body']), 'Successfully processed CloudWatch Logs')

    @patch('lambda_function.sns_client')
    @patch('lambda_function.urllib.request.Request')
    @patch('lambda_function.urllib.request.urlopen')
    def test_cloudwatch_alarm_with_slack(self, mock_urlopen, mock_request, mock_sns_client):
        """Test handling a CloudWatch Alarm with Slack enabled"""
        # Set environment variables for Slack
        os.environ['ENABLE_SLACK'] = 'true'
        os.environ['SLACK_WEBHOOK_URL'] = 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'
        os.environ['SLACK_CHANNEL'] = '#test-channel'
        os.environ['SLACK_USERNAME'] = 'CloudWatch-Bot'

        # Configure mocks
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        mock_sns_client.publish.return_value = {'MessageId': 'test-message-id'}

        # Create a CloudWatch Alarm message
        cloudwatch_alarm = {
            "AlarmName": "test-alarm",
            "AlarmDescription": "This is a test alarm",
            "AWSAccountId": "123456789012",
            "NewStateValue": "ALARM",
            "NewStateReason": "Threshold Crossed",
            "StateChangeTime": "2023-01-01T00:00:00.000+0000",
            "Region": "us-east-1",
            "OldStateValue": "OK",
            "Trigger": {
                "MetricName": "CPUUtilization",
                "Namespace": "AWS/EC2",
                "StatisticType": "Statistic",
                "Statistic": "AVERAGE",
                "Unit": None,
                "Dimensions": [],
                "Period": 300,
                "EvaluationPeriods": 1,
                "ComparisonOperator": "GreaterThanThreshold",
                "Threshold": 80.0
            }
        }

        # Wrap it in an SNS event
        sns_message = json.dumps(cloudwatch_alarm)
        event = {
            "Records": [
                {
                    "EventSource": "aws:sns",
                    "EventVersion": "1.0",
                    "EventSubscriptionArn": "arn:aws:sns:us-east-1:123456789012:test-topic:subscription-id",
                    "Sns": {
                        "Type": "Notification",
                        "MessageId": "12345678-1234-1234-1234-123456789012",
                        "TopicArn": "arn:aws:sns:us-east-1:123456789012:test-topic",
                        "Subject": "Test Subject",
                        "Message": sns_message,
                        "Timestamp": "2023-01-01T00:00:00.000Z",
                        "SignatureVersion": "1",
                        "Signature": "test-signature",
                        "SigningCertUrl": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-12345.pem",
                        "UnsubscribeUrl": "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:123456789012:test-topic:subscription-id",
                        "MessageAttributes": {}
                    }
                }
            ]
        }

        # Call the Lambda handler
        result = lambda_function.lambda_handler(event, {})

        # Check if SNS publish was called
        mock_sns_client.publish.assert_called_once()

        # Check if Slack webhook was called
        mock_request.assert_called_once()
        mock_urlopen.assert_called_once()

        # Get the actual call arguments
        call_args = mock_request.call_args
        actual_data = json.loads(call_args[1]['data'].decode('utf-8'))

        # Verify the structure of the Slack message
        self.assertEqual(actual_data['channel'], '#test-channel')
        self.assertEqual(actual_data['username'], 'CloudWatch-Bot')
        self.assertTrue('attachments' in actual_data)

        # Verify the attachment structure
        attachment = actual_data['attachments'][0]
        self.assertEqual(attachment['color'], 'danger')
        self.assertEqual(attachment['title'], 'CloudWatch Alarm: test-alarm')

        # Verify the fields
        fields = attachment['fields']
        self.assertEqual(len(fields), 4)

        # Find fields by title
        state_field = next((f for f in fields if f['title'] == 'State'), None)
        self.assertIsNotNone(state_field)
        self.assertEqual(state_field['value'], 'ALARM')

        region_field = next((f for f in fields if f['title'] == 'Region'), None)
        self.assertIsNotNone(region_field)
        self.assertEqual(region_field['value'], 'us-east-1')

        desc_field = next((f for f in fields if f['title'] == 'Description'), None)
        self.assertIsNotNone(desc_field)
        self.assertEqual(desc_field['value'], 'This is a test alarm')

        reason_field = next((f for f in fields if f['title'] == 'Reason'), None)
        self.assertIsNotNone(reason_field)
        self.assertEqual(reason_field['value'], 'Threshold Crossed')

        # Check the response
        self.assertEqual(result['statusCode'], 200)
        self.assertEqual(json.loads(result['body']), 'Successfully processed CloudWatch Logs')

        # Clean up
        del os.environ['ENABLE_SLACK']
        del os.environ['SLACK_WEBHOOK_URL']
        del os.environ['SLACK_CHANNEL']
        del os.environ['SLACK_USERNAME']


if __name__ == '__main__':
    unittest.main()

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
        # Create an event with unknown format
        event = {
            "some_key": "some_value"
        }

        # Call the Lambda handler
        result = lambda_function.lambda_handler(event, {})

        # Check that SNS publish was not called
        mock_sns_client.publish.assert_not_called()

        # Check the response has error status code
        self.assertEqual(result['statusCode'], 400)
        self.assertEqual(json.loads(result['body']), 'Unknown event format')


if __name__ == '__main__':
    unittest.main()

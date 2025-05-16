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


if __name__ == '__main__':
    unittest.main()

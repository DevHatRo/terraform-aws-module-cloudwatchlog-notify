#!/usr/bin/env python3
"""
Script to generate a CloudWatch Logs test event for Lambda testing.
Creates a properly formatted test event with gzip compression and base64 encoding.
"""
import base64
import gzip
import json
import os
import sys

def create_test_event(output_file="test-event.json"):
    """
    Create a test CloudWatch Logs event file for Lambda testing.

    Args:
        output_file (str): Path to the output file
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

    # Write to output file
    with open(output_file, "w") as f:
        json.dump(event, f)

    print(f"Created test event file: {output_file}")

    # Optionally print the content
    with open(output_file, "r") as f:
        print(f.read())

if __name__ == "__main__":
    # Use command line argument for output file if provided
    output_file = sys.argv[1] if len(sys.argv) > 1 else "test-event.json"
    create_test_event(output_file)

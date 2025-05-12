#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# LocalStack endpoint
LOCALSTACK_ENDPOINT="http://localhost:4566"

# Function to check if LocalStack is running
check_localstack() {
    echo "Checking LocalStack status..."
    if curl -s "${LOCALSTACK_ENDPOINT}/health" | grep -q '"lambda": "running"'; then
        echo -e "${GREEN}LocalStack is running${NC}"
        return 0
    else
        echo -e "${RED}LocalStack is not running${NC}"
        return 1
    fi
}

# Function to create SNS topic
create_sns_topic() {
    echo "Creating SNS topic..."
    TOPIC_ARN=$(aws --endpoint-url="${LOCALSTACK_ENDPOINT}" sns create-topic --name cloudwatch-notifier-topic --query 'TopicArn' --output text)
    echo "Created SNS topic: ${TOPIC_ARN}"
    echo "${TOPIC_ARN}" > .localstack/topic-arn.txt
}

# Function to create Lambda function
create_lambda_function() {
    echo "Creating Lambda function..."
    aws --endpoint-url="${LOCALSTACK_ENDPOINT}" lambda create-function \
        --function-name cloudwatch-notifier \
        --runtime provided.al2 \
        --handler main \
        --zip-file fileb://function.zip \
        --role arn:aws:iam::000000000000:role/lambda-role \
        --environment "Variables={SNS_ARN=$(cat .localstack/topic-arn.txt),AWS_REGION=us-east-1}"
}

# Function to create test event
create_test_event() {
    echo "Creating test event..."
    cat > .localstack/test-event.json << EOF
{
    "awslogs": {
        "data": "$(echo '{"logGroup":"/aws/lambda/test-function","logStream":"2024/01/01/[$LATEST]1234567890","logEvents":[{"message":"{\"log\":\"test error\",\"kubernetes\":{\"pod_name\":\"test-pod\",\"namespace_name\":\"test-namespace\",\"container_name\":\"test-app\"}}"}]}' | base64)"
    }
}
EOF
}

# Function to invoke Lambda function
invoke_lambda() {
    echo "Invoking Lambda function..."
    aws --endpoint-url="${LOCALSTACK_ENDPOINT}" lambda invoke \
        --function-name cloudwatch-notifier \
        --payload file://.localstack/test-event.json \
        .localstack/output.json

    echo "Lambda output:"
    cat .localstack/output.json
}

# Main execution
main() {
    # Create .localstack directory
    mkdir -p .localstack

    # Check if LocalStack is running
    check_localstack || exit 1

    # Create SNS topic
    create_sns_topic

    # Create Lambda function
    create_lambda_function

    # Create test event
    create_test_event

    # Invoke Lambda function
    invoke_lambda
}

# Run main function
main 

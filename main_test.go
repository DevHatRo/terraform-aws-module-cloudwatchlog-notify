package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"os"
	"testing"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-sdk-go-v2/service/sns"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

// MockSNSClient is a mock implementation of the SNS client
type MockSNSClient struct {
	mock.Mock
}

func (m *MockSNSClient) Publish(ctx context.Context, params *sns.PublishInput, optFns ...func(*sns.Options)) (*sns.PublishOutput, error) {
	args := m.Called(ctx, params)
	return args.Get(0).(*sns.PublishOutput), args.Error(1)
}

func TestNewConfig(t *testing.T) {
	// Test case 1: Missing SNS_ARN
	os.Unsetenv("SNS_ARN")
	os.Unsetenv("AWS_REGION")
	_, err := NewConfig()
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "SNS_ARN environment variable is not set")

	// Test case 2: Missing AWS_REGION
	os.Setenv("SNS_ARN", "arn:aws:sns:region:account:topic")
	_, err = NewConfig()
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "AWS_REGION environment variable is not set")

	// Test case 3: Valid configuration
	os.Setenv("AWS_REGION", "us-west-2")
	cfg, err := NewConfig()
	assert.NoError(t, err)
	assert.Equal(t, "arn:aws:sns:region:account:topic", cfg.SNSARN)
	assert.Equal(t, "us-west-2", cfg.Region)
}

func TestLogPayload(t *testing.T) {
	// Create a test payload
	testPayload := LogPayload{
		LogGroup:  "test-group",
		LogStream: "test-stream",
		LogEvents: []LogEvent{
			{
				Message: `{"log": "test error", "kubernetes": {"pod_name": "test-pod", "namespace_name": "test-namespace", "container_name": "test-app"}}`,
			},
		},
	}

	// Encode the payload
	jsonData, err := json.Marshal(testPayload)
	assert.NoError(t, err)
	encodedData := base64.StdEncoding.EncodeToString(jsonData)

	// Create a test event
	event := events.CloudwatchLogsEvent{
		AWSLogs: events.CloudwatchLogsRawData{
			Data: encodedData,
		},
	}

	// Create a handler with mock SNS client
	mockSNS := new(MockSNSClient)
	handler := &LambdaHandler{
		snsClient: mockSNS,
		config: Config{
			SNSARN: "arn:aws:sns:region:account:topic",
		},
	}

	// Test logPayload
	payload, err := handler.logPayload(event)
	assert.NoError(t, err)
	assert.Equal(t, testPayload.LogGroup, payload.LogGroup)
	assert.Equal(t, testPayload.LogStream, payload.LogStream)
	assert.Len(t, payload.LogEvents, 1)
}

func TestPublishMessage(t *testing.T) {
	// Create a test handler with mock SNS client
	mockSNS := new(MockSNSClient)
	handler := &LambdaHandler{
		snsClient: mockSNS,
		config: Config{
			SNSARN: "arn:aws:sns:region:account:topic",
		},
	}

	// Set up mock expectations
	mockSNS.On("Publish", mock.Anything, mock.MatchedBy(func(input *sns.PublishInput) bool {
		return *input.TopicArn == "arn:aws:sns:region:account:topic" &&
			*input.Subject == "🚨 Error Alert: Lambda - test-func"
	})).Return(&sns.PublishOutput{}, nil)

	// Test publishMessage
	err := handler.publishMessage(
		context.Background(),
		"test-group",
		"test-stream",
		"test error",
		[]string{"", "", "", "test-func"},
		"test-pod",
		"test-namespace",
		"test-app",
	)
	assert.NoError(t, err)
	mockSNS.AssertExpectations(t)
}

func TestErrorDetails(t *testing.T) {
	// Create a test payload
	testPayload := &LogPayload{
		LogGroup:  "test-group",
		LogStream: "test-stream",
		LogEvents: []LogEvent{
			{
				Message: `{"log": "test error", "kubernetes": {"pod_name": "test-pod", "namespace_name": "test-namespace", "container_name": "test-app"}}`,
			},
		},
	}

	// Create a handler with mock SNS client
	mockSNS := new(MockSNSClient)
	handler := &LambdaHandler{
		snsClient: mockSNS,
		config: Config{
			SNSARN: "arn:aws:sns:region:account:topic",
		},
	}

	// Set up mock expectations
	mockSNS.On("Publish", mock.Anything, mock.MatchedBy(func(input *sns.PublishInput) bool {
		return *input.TopicArn == "arn:aws:sns:region:account:topic"
	})).Return(&sns.PublishOutput{}, nil)

	// Test errorDetails
	err := handler.errorDetails(context.Background(), testPayload)
	assert.NoError(t, err)
	mockSNS.AssertExpectations(t)
}

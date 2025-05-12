package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/sns"
	"github.com/aws/aws-sdk-go-v2/service/sns/types"
	"go.uber.org/zap"
)

// Custom errors
var (
	ErrInvalidConfig    = fmt.Errorf("invalid configuration")
	ErrInvalidInput     = fmt.Errorf("invalid input")
	ErrSNSPublishFailed = fmt.Errorf("failed to publish to SNS")
	ErrLogParseFailed   = fmt.Errorf("failed to parse log data")
	ErrLogDecodeFailed  = fmt.Errorf("failed to decode log data")
)

// Config holds the application configuration
type Config struct {
	SNSARN string
	Region string
}

// LogEvent represents a single log event
type LogEvent struct {
	Message string `json:"message"`
}

// LogPayload represents the CloudWatch logs payload
type LogPayload struct {
	LogGroup  string     `json:"logGroup"`
	LogStream string     `json:"logStream"`
	LogEvents []LogEvent `json:"logEvents"`
}

// KubernetesData represents Kubernetes metadata
type KubernetesData struct {
	PodName       string `json:"pod_name"`
	NamespaceName string `json:"namespace_name"`
	ContainerName string `json:"container_name"`
}

// ParsedLogData represents the parsed log message
type ParsedLogData struct {
	Log        string         `json:"log"`
	Kubernetes KubernetesData `json:"kubernetes"`
}

// LambdaHandler handles Lambda function requests
type LambdaHandler struct {
	snsClient *sns.Client
	config    Config
	logger    *zap.Logger
}

// NewConfig creates a new Config instance
func NewConfig() (Config, error) {
	snsARN := os.Getenv("SNS_ARN")
	if snsARN == "" {
		return Config{}, fmt.Errorf("%w: SNS_ARN environment variable is not set", ErrInvalidConfig)
	}

	region := os.Getenv("AWS_REGION")
	if region == "" {
		return Config{}, fmt.Errorf("%w: AWS_REGION environment variable is not set", ErrInvalidConfig)
	}

	return Config{
		SNSARN: snsARN,
		Region: region,
	}, nil
}

// NewLambdaHandler creates a new LambdaHandler instance
func NewLambdaHandler() (*LambdaHandler, error) {
	// Initialize logger
	logger, err := zap.NewProduction()
	if err != nil {
		return nil, fmt.Errorf("failed to initialize logger: %w", err)
	}

	// Load configuration
	cfg, err := NewConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to load configuration: %w", err)
	}

	// Initialize AWS SDK config
	awsCfg, err := config.LoadDefaultConfig(context.Background(),
		config.WithRegion(cfg.Region),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	return &LambdaHandler{
		snsClient: sns.NewFromConfig(awsCfg),
		config:    cfg,
		logger:    logger,
	}, nil
}

// logPayload decodes and parses the CloudWatch logs payload
func (h *LambdaHandler) logPayload(event events.CloudwatchLogsEvent) (*LogPayload, error) {
	if event.AWSLogs.Data == "" {
		return nil, fmt.Errorf("%w: empty log data", ErrInvalidInput)
	}

	decodedData, err := base64.StdEncoding.DecodeString(event.AWSLogs.Data)
	if err != nil {
		return nil, fmt.Errorf("%w: %v", ErrLogDecodeFailed, err)
	}

	var payload LogPayload
	if err := json.Unmarshal(decodedData, &payload); err != nil {
		return nil, fmt.Errorf("%w: %v", ErrLogParseFailed, err)
	}

	if len(payload.LogEvents) == 0 {
		return nil, fmt.Errorf("%w: no log events found", ErrInvalidInput)
	}

	return &payload, nil
}

// formatMessage formats the notification message
func formatMessage(appName, logGroup, logStream, namespaceName, podName, errorMsg string) string {
	return fmt.Sprintf(
		"🚨 *Application Error Alert* 🚨\n\n"+
			"*Application:* %s\n"+
			"*LogGroup:* %s\n"+
			"*LogStream:* %s\n"+
			"*Namespace:* %s\n"+
			"*Pod Name:* %s\n\n"+
			"*Error Message:*\n```\n%s\n```\n",
		strings.ToUpper(appName),
		logGroup,
		logStream,
		namespaceName,
		podName,
		errorMsg,
	)
}

// publishMessage publishes a message to SNS
func (h *LambdaHandler) publishMessage(ctx context.Context, logGroup, logStream, errorMsg string, lambdaFuncName []string, podName, namespaceName, appName string) error {
	if len(lambdaFuncName) < 4 {
		return fmt.Errorf("%w: invalid lambda function name format", ErrInvalidInput)
	}

	message := formatMessage(appName, logGroup, logStream, namespaceName, podName, errorMsg)
	subject := fmt.Sprintf("🚨 Error Alert: Lambda - %s", lambdaFuncName[3])

	input := &sns.PublishInput{
		Message:  &message,
		Subject:  &subject,
		TopicArn: &h.config.SNSARN,
	}

	// Add timeout to context
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	_, err := h.snsClient.Publish(ctx, input)
	if err != nil {
		var snsErr *types.InvalidParameterException
		if errors.As(err, &snsErr) {
			return fmt.Errorf("%w: invalid parameters: %v", ErrSNSPublishFailed, err)
		}
		return fmt.Errorf("%w: %v", ErrSNSPublishFailed, err)
	}

	return nil
}

// errorDetails processes log events and publishes notifications
func (h *LambdaHandler) errorDetails(ctx context.Context, payload *LogPayload) error {
	logGroup := payload.LogGroup
	logStream := payload.LogStream
	lambdaFuncName := strings.Split(logGroup, "/")

	for _, logEvent := range payload.LogEvents {
		var parsedData ParsedLogData
		if err := json.Unmarshal([]byte(logEvent.Message), &parsedData); err != nil {
			h.logger.Error("Failed to parse log event",
				zap.Error(err),
				zap.String("message", logEvent.Message),
			)
			continue
		}

		if err := h.publishMessage(
			ctx,
			logGroup,
			logStream,
			parsedData.Log,
			lambdaFuncName,
			parsedData.Kubernetes.PodName,
			parsedData.Kubernetes.NamespaceName,
			parsedData.Kubernetes.ContainerName,
		); err != nil {
			h.logger.Error("Failed to publish message",
				zap.Error(err),
				zap.String("pod", parsedData.Kubernetes.PodName),
				zap.String("namespace", parsedData.Kubernetes.NamespaceName),
			)
			return err
		}
	}

	return nil
}

// HandleRequest handles Lambda function requests
func (h *LambdaHandler) HandleRequest(ctx context.Context, event events.CloudwatchLogsEvent) (map[string]interface{}, error) {
	h.logger.Info("Processing CloudWatch logs event",
		zap.String("data", event.AWSLogs.Data),
	)

	payload, err := h.logPayload(event)
	if err != nil {
		h.logger.Error("Failed to process log payload",
			zap.Error(err),
		)
		return map[string]interface{}{
			"statusCode": 500,
			"body": map[string]string{
				"message": "Exception",
				"result":  err.Error(),
			},
		}, nil
	}

	if err := h.errorDetails(ctx, payload); err != nil {
		h.logger.Error("Failed to process error details",
			zap.Error(err),
		)
		return map[string]interface{}{
			"statusCode": 500,
			"body": map[string]string{
				"message": "Exception",
				"result":  err.Error(),
			},
		}, nil
	}

	h.logger.Info("Successfully processed and sent notifications")
	return map[string]interface{}{
		"statusCode": 200,
		"body": map[string]string{
			"message": "Success",
		},
	}, nil
}

func main() {
	handler, err := NewLambdaHandler()
	if err != nil {
		panic(fmt.Sprintf("Failed to create Lambda handler: %v", err))
	}

	lambda.Start(handler.HandleRequest)
}

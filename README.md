# CloudWatch Logs Notification Module for AWS

[![codecov](https://codecov.io/gh/DevHatRo/terraform-aws-module-cloudwatchlog-notify/graph/badge.svg?token=UPRDDCJZ1P)](https://codecov.io/gh/DevHatRo/terraform-aws-module-cloudwatchlog-notify)

This Terraform module deploys a complete solution for receiving CloudWatch Logs events and sending notifications through SNS.

## Architecture

This module sets up:

1. A Lambda function that processes CloudWatch Logs events
2. An SNS topic that receives notifications from the Lambda function
3. CloudWatch Logs subscription filters for the specified log groups
4. All necessary IAM permissions and policies

The Lambda function supports:
- Processing CloudWatch Logs events directly
- Processing events via SNS
- Parsing JSON log messages, including Kubernetes logs
- Custom formatting for different log types

## Usage

```hcl
module "cloudwatch_logs_notifier" {
  source  = "github.com/DevHatRo/terraform-aws-module-cloudwatchlog-notify"
  
  # Basic configuration
  function_name          = "logs-error-notifier"
  sns_topic_name         = "logs-error-alerts"
  
  # Email subscribers to receive notifications
  email_subscribers      = [
    "alerts@example.com",
    "devops@example.com"
  ]
  
  # CloudWatch log groups to monitor
  log_group_subscriptions = [
    "/aws/lambda/important-function",
    "/aws/eks/my-cluster/application-logs"
  ]
  
  # Filter pattern (customize for your needs)
  filter_pattern         = "{$.kubernetes.namespace_name = \"*\" && $.log = \"*error*\"}"

  # Custom tags
  tags = {
    Environment = "Production"
    Project     = "Monitoring"
    ManagedBy   = "terraform"
  }
}
```

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.0 |
| aws | >= 4.9 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| lambda_function | terraform-aws-modules/lambda/aws | ~> 7.21 |
| sns | terraform-aws-modules/sns/aws | ~> 6.1 |

## Resources

| Name | Type |
|------|------|
| aws_cloudwatch_log_subscription_filter.this | resource |
| aws_lambda_permission.allow_cloudwatch | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| create_lambda_function | Whether to create the Lambda function | `bool` | `true` | no |
| enabled | Whether to enable all resources | `bool` | `true` | no |
| create_sns_topic | Whether to create the SNS topic | `bool` | `true` | no |
| create_cloudwatch_log_subscription_filter | Whether to create the CloudWatch log subscription filter | `bool` | `true` | no |
| function_name | The name of the Lambda function | `string` | `"cloudwatch-logs-notifier"` | no |
| cloudwatch_log_group_retention_in_days | The number of days to retain Lambda logs | `number` | `14` | no |
| cloudwatch_log_group_kms_key_id | The ARN of the KMS Key to use when encrypting log data for Lambda | `string` | `null` | no |
| sns_topic_name | The name of the SNS topic for notifications | `string` | `"cloudwatch-logs-notifications"` | no |
| email_subscribers | List of email addresses to subscribe to the SNS topic | `list(string)` | `[]` | no |
| log_group_subscriptions | List of CloudWatch log groups to subscribe to | `list(string)` | `[]` | no |
| filter_pattern | The filter pattern to use for CloudWatch log subscriptions | `string` | `"{$.kubernetes.namespace_name = \"*\" && $.kubernetes.pod_name = \"*\" && $.kubernetes.container_name = \"*\" && $.log = \"*\"}"` | no |
| tags | A map of tags to apply to all resources | `map(string)` | `{ "ManagedBy": "terraform" }` | no |
| additional_policy_statements | Additional IAM policy statements to attach to the Lambda function | `any` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| lambda_function_arn | The ARN of the Lambda function |
| lambda_function_name | The name of the Lambda function |
| lambda_function_invoke_arn | The invocation ARN of the Lambda function |
| cloudwatch_log_group_name | The name of the CloudWatch log group for the Lambda function |
| sns_topic_arn | The ARN of the SNS topic for CloudWatch log notifications |
| sns_topic_name | The name of the SNS topic for CloudWatch log notifications |
| lambda_role_arn | The ARN of the IAM role used by the Lambda function |
| lambda_role_name | The name of the IAM role used by the Lambda function |
<!-- END_TF_DOCS -->

## How It Works

1. CloudWatch Logs subscription filters are created for the specified log groups
2. When a log matches the filter pattern, it's sent to the Lambda function
3. The Lambda function processes the log data:
   - Extracts useful information from the log message
   - Formats it into a readable notification
   - Sends the notification to the SNS topic
4. The SNS topic delivers the notification to all subscribed email addresses

## License

MIT

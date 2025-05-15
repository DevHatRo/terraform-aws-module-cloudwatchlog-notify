# CloudWatch Logs Notification Module for AWS

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

## Usage

```hcl
module "cloudwatch_logs_notifier" {
  source = "github.com/your-repo/terraform-aws-module-cloudwatchlog-notify"

  function_name          = "cloudwatch-logs-notifier"
  sns_topic_name         = "cloudwatch-logs-notifications"
  email_subscribers      = ["alerts@example.com"]
  log_group_subscriptions = [
    "/aws/lambda/my-function",
    "/aws/eks/my-cluster/cluster"
  ]
  filter_pattern         = "{$.level = \"error\" || $.level = \"ERROR\"}"

  tags = {
    Environment = "Production"
    Project     = "Monitoring"
  }
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.0 |
| aws | >= 4.9 |
| archive | >= 2.0 |

## Providers

| Name | Version |
|------|---------|
| aws | >= 4.9 |
| archive | >= 2.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| lambda_function | terraform-aws-modules/lambda/aws | ~> 4.0 |
| sns | terraform-aws-modules/sns/aws | ~> 3.0 |

## Resources

| Name | Type |
|------|------|
| aws_cloudwatch_log_subscription_filter.this | resource |
| aws_lambda_permission.cloudwatch_logs | resource |
| aws_lambda_permission.sns | resource |
| aws_sns_topic_subscription.lambda | resource |
| aws_sns_topic_subscription.email | resource |
| aws_caller_identity.current | data source |
| archive_file.lambda_package | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| region | The AWS region to deploy the resources in | `string` | `"us-east-1"` | no |
| function_name | The name of the Lambda function | `string` | `"cloudwatch-logs-notifier"` | no |
| cloudwatch_log_group_retention_in_days | The number of days to retain Lambda logs | `number` | `14` | no |
| cloudwatch_log_group_kms_key_id | The ARN of the KMS Key to use when encrypting log data for Lambda | `string` | `null` | no |
| sns_topic_name | The name of the SNS topic for notifications | `string` | `"cloudwatch-logs-notifications"` | no |
| email_subscribers | List of email addresses to subscribe to the SNS topic | `list(string)` | `[]` | no |
| log_group_subscriptions | List of CloudWatch log groups to subscribe to | `list(string)` | `[]` | no |
| filter_pattern | The filter pattern to use for CloudWatch log subscriptions | `string` | `"{$.kubernetes.namespace_name = \"*\" && $.kubernetes.pod_name = \"*\" && $.kubernetes.container_name = \"*\" && $.log = \"*\"}"` | no |
| tags | A map of tags to apply to all resources | `map(string)` | `{ "ManagedBy": "terraform" }` | no |

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

## License

MIT

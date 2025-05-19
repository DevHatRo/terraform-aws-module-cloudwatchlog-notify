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
- Processing CloudWatch Alarm notifications

## Features

### Email Notifications

The module can send CloudWatch Logs alerts to email subscribers through Amazon SNS.

```hcl
module "cloudwatch_logs_notifier" {
  source = "github.com/username/terraform-aws-module-cloudwatchlog-notify"

  email_subscribers = ["alerts@example.com", "team@example.com"]
  email_subject     = "AWS CloudWatch Alert"  # Customize the email subject
  log_group_subscriptions = ["/aws/lambda/my-function", "/aws/eks/my-cluster/cluster"]
}
```

### Slack Notifications

The module can also send CloudWatch Logs alerts to Slack channels through webhooks.

```hcl
module "cloudwatch_logs_notifier" {
  source = "github.com/username/terraform-aws-module-cloudwatchlog-notify"

  enable_slack_notifications = true
  slack_webhook_url = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
  slack_channel = "#alerts"
  slack_username = "CloudWatch Logs Bot"

  log_group_subscriptions = ["/aws/lambda/my-function", "/aws/eks/my-cluster/cluster"]
}
```

### CloudWatch Alarm SNS Topic

The module can create a dedicated SNS topic for CloudWatch Alarms to trigger the Lambda function. This allows you to have your CloudWatch Alarms send notifications through the same pipeline as your CloudWatch Logs.

```hcl
module "cloudwatch_logs_notifier" {
  source = "github.com/username/terraform-aws-module-cloudwatchlog-notify"

  # Enable CloudWatch Alarm SNS Topic
  create_cloudwatch_alarm_sns_topic = true
  cloudwatch_alarm_sns_topic_name   = "my-alarm-topic"

  # Configure notification channels
  enable_slack_notifications = true
  slack_webhook_url = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
  slack_channel = "#alerts"

  email_subscribers = ["alerts@example.com"]
}

# Example CloudWatch Alarm that sends to the CloudWatch Alarm SNS topic
resource "aws_cloudwatch_metric_alarm" "example" {
  alarm_name          = "example-high-cpu-alarm"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "This metric monitors Lambda function CPU utilization"
  alarm_actions       = [module.cloudwatch_logs_notifier.cloudwatch_alarm_sns_topic_arn]
  ok_actions          = [module.cloudwatch_logs_notifier.cloudwatch_alarm_sns_topic_arn]

  dimensions = {
    FunctionName = "my-lambda-function"
  }
}
```

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | >= 4.9 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | >= 4.9 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_lambda_function"></a> [lambda\_function](#module\_lambda\_function) | terraform-aws-modules/lambda/aws | 7.21.0 |
| <a name="module_sns"></a> [sns](#module\_sns) | terraform-aws-modules/sns/aws | 6.1.3 |

## Resources

| Name | Type |
|------|------|
| [aws_cloudwatch_log_subscription_filter.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_subscription_filter) | resource |
| [aws_caller_identity.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/caller_identity) | data source |
| [aws_region.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/region) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_additional_policy_statements"></a> [additional\_policy\_statements](#input\_additional\_policy\_statements) | Additional IAM policy statements to attach to the Lambda function | `any` | `{}` | no |
| <a name="input_cloudwatch_alarm_sns_topic_name"></a> [cloudwatch\_alarm\_sns\_topic\_name](#input\_cloudwatch\_alarm\_sns\_topic\_name) | The name of the SNS topic for CloudWatch alarm notifications | `string` | `"cloudwatch-alarm-notifications"` | no |
| <a name="input_cloudwatch_log_group_kms_key_id"></a> [cloudwatch\_log\_group\_kms\_key\_id](#input\_cloudwatch\_log\_group\_kms\_key\_id) | The ARN of the KMS Key to use when encrypting log data for Lambda | `string` | `null` | no |
| <a name="input_cloudwatch_log_group_retention_in_days"></a> [cloudwatch\_log\_group\_retention\_in\_days](#input\_cloudwatch\_log\_group\_retention\_in\_days) | The number of days to retain Lambda logs | `number` | `14` | no |
| <a name="input_create_cloudwatch_alarm_sns_topic"></a> [create\_cloudwatch\_alarm\_sns\_topic](#input\_create\_cloudwatch\_alarm\_sns\_topic) | Whether to create an SNS topic for CloudWatch alarms | `bool` | `false` | no |
| <a name="input_create_cloudwatch_log_subscription_filter"></a> [create\_cloudwatch\_log\_subscription\_filter](#input\_create\_cloudwatch\_log\_subscription\_filter) | Whether to create the CloudWatch log subscription filter | `bool` | `true` | no |
| <a name="input_create_lambda_function"></a> [create\_lambda\_function](#input\_create\_lambda\_function) | Whether to create the Lambda function | `bool` | `true` | no |
| <a name="input_create_sns_topic"></a> [create\_sns\_topic](#input\_create\_sns\_topic) | Whether to create the SNS topic | `bool` | `true` | no |
| <a name="input_email_subscribers"></a> [email\_subscribers](#input\_email\_subscribers) | List of email addresses to subscribe to the SNS topic | `list(string)` | `[]` | no |
| <a name="input_enable_slack_notifications"></a> [enable\_slack\_notifications](#input\_enable\_slack\_notifications) | Whether to enable Slack notifications | `bool` | `false` | no |
| <a name="input_enabled"></a> [enabled](#input\_enabled) | Whether to enable all resources | `bool` | `true` | no |
| <a name="input_filter_pattern"></a> [filter\_pattern](#input\_filter\_pattern) | The filter pattern to use for CloudWatch log subscriptions | `string` | `"{$.kubernetes.namespace_name = \"*\" && $.kubernetes.pod_name = \"*\" && $.kubernetes.container_name = \"*\" && $.log = \"*\"}"` | no |
| <a name="input_function_name"></a> [function\_name](#input\_function\_name) | The name of the Lambda function | `string` | `"cloudwatch-logs-notifier"` | no |
| <a name="input_log_group_subscriptions"></a> [log\_group\_subscriptions](#input\_log\_group\_subscriptions) | List of CloudWatch log groups to subscribe to | `list(string)` | `[]` | no |
| <a name="input_slack_channel"></a> [slack\_channel](#input\_slack\_channel) | The Slack channel to send notifications to | `string` | `""` | no |
| <a name="input_slack_username"></a> [slack\_username](#input\_slack\_username) | The username to display for Slack notifications | `string` | `"CloudWatch Logs"` | no |
| <a name="input_slack_webhook_url"></a> [slack\_webhook\_url](#input\_slack\_webhook\_url) | The Slack webhook URL for notifications | `string` | `""` | no |
| <a name="input_sns_topic_name"></a> [sns\_topic\_name](#input\_sns\_topic\_name) | The name of the SNS topic for notifications | `string` | `"cloudwatch-logs-notifications"` | no |
| <a name="input_tags"></a> [tags](#input\_tags) | A map of tags to apply to all resources | `map(string)` | <pre>{<br/>  "ManagedBy": "terraform"<br/>}</pre> | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_cloudwatch_alarm_sns_topic_arn"></a> [cloudwatch\_alarm\_sns\_topic\_arn](#output\_cloudwatch\_alarm\_sns\_topic\_arn) | The ARN of the SNS topic for CloudWatch alarm notifications |
| <a name="output_cloudwatch_alarm_sns_topic_name"></a> [cloudwatch\_alarm\_sns\_topic\_name](#output\_cloudwatch\_alarm\_sns\_topic\_name) | The name of the SNS topic for CloudWatch alarm notifications |
| <a name="output_cloudwatch_log_group_name"></a> [cloudwatch\_log\_group\_name](#output\_cloudwatch\_log\_group\_name) | The name of the CloudWatch log group for the Lambda function |
| <a name="output_lambda_function_arn"></a> [lambda\_function\_arn](#output\_lambda\_function\_arn) | The ARN of the Lambda function |
| <a name="output_lambda_function_invoke_arn"></a> [lambda\_function\_invoke\_arn](#output\_lambda\_function\_invoke\_arn) | The invocation ARN of the Lambda function |
| <a name="output_lambda_function_name"></a> [lambda\_function\_name](#output\_lambda\_function\_name) | The name of the Lambda function |
| <a name="output_lambda_role_arn"></a> [lambda\_role\_arn](#output\_lambda\_role\_arn) | The ARN of the IAM role used by the Lambda function |
| <a name="output_lambda_role_name"></a> [lambda\_role\_name](#output\_lambda\_role\_name) | The name of the IAM role used by the Lambda function |
| <a name="output_sns_topic_arn"></a> [sns\_topic\_arn](#output\_sns\_topic\_arn) | The ARN of the SNS topic for CloudWatch log notifications |
| <a name="output_sns_topic_name"></a> [sns\_topic\_name](#output\_sns\_topic\_name) | The name of the SNS topic for CloudWatch log notifications |
<!-- END_TF_DOCS -->

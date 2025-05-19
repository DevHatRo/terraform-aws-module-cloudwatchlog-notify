terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.9"
    }
  }
}

provider "aws" {
  region = local.region
}

locals {
  region = "us-east-1"
  name   = "cloudwatch-logs-notifier-example"

  tags = {
    Owner       = "user"
    Environment = "dev"
    Terraform   = "true"
  }
}

################################################################################
# CloudWatch Logs Notifier Module
################################################################################

module "cloudwatch_logs_notifier" {
  source = "../.."

  function_name = local.name

  # SNS and Email configuration
  sns_topic_name    = "${local.name}-topic"
  email_subscribers = ["alerts@example.com"]

  # Slack configuration
  enable_slack_notifications = true
  slack_webhook_url          = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
  slack_channel              = "#alerts"
  slack_username             = "CloudWatch Alert Bot"

  # CloudWatch Logs subscription configuration
  log_group_subscriptions = [
    "/aws/lambda/example-function",
    "/aws/eks/example-cluster/cluster"
  ]

  # Custom filter pattern for Kubernetes logs with errors
  filter_pattern = "{$.kubernetes.namespace_name = \"*\" && $.kubernetes.pod_name = \"*\" && $.kubernetes.container_name = \"*\" && $.log = \"*ERROR*\"}"

  # CloudWatch Alarm SNS Topic configuration
  create_cloudwatch_alarm_sns_topic = true
  cloudwatch_alarm_sns_topic_name   = "${local.name}-alarms"

  tags = local.tags
}

################################################################################
# Supporting Resources
################################################################################

# Example Lambda function that will be monitored
module "lambda_function" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name = "example-function"
  description   = "Example Lambda function that will be monitored"
  handler       = "index.handler"
  runtime       = "nodejs18.x"

  source_path = "${path.module}/src/example-function"

  tags = local.tags
}

# Create a dummy log group for the example
resource "aws_cloudwatch_log_group" "example" {
  name              = "/aws/eks/example-cluster/cluster"
  retention_in_days = 1

  tags = local.tags
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
    FunctionName = module.lambda_function.lambda_function_name
  }

  tags = local.tags
}

# Output the module outputs
output "lambda_function_name" {
  description = "The name of the Lambda function"
  value       = module.cloudwatch_logs_notifier.lambda_function_name
}

output "sns_topic_arn" {
  description = "The ARN of the SNS topic for CloudWatch log notifications"
  value       = module.cloudwatch_logs_notifier.sns_topic_arn
}

output "cloudwatch_alarm_sns_topic_arn" {
  description = "The ARN of the SNS topic for CloudWatch alarm notifications"
  value       = module.cloudwatch_logs_notifier.cloudwatch_alarm_sns_topic_arn
}

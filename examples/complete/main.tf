provider "aws" {
  region = "us-west-2"
}

module "cloudwatch_logs_notifier" {
  source = "../../"

  function_name  = "logs-error-notifier"
  sns_topic_name = "logs-error-alerts"

  # Subscribe these email addresses to the SNS topic
  email_subscribers = [
    "alerts@example.com",
    "devops@example.com"
  ]

  # Monitor these CloudWatch log groups
  log_group_subscriptions = [
    "/aws/eks/my-cluster/application-logs",
    "/aws/lambda/important-function"
  ]

  # Custom filter pattern (customize to your needs)
  filter_pattern = "{$.kubernetes.namespace_name = \"*\" && $.log = \"*error*\"}"

  # Add custom tags
  tags = {
    Environment = "production"
    Project     = "monitoring"
    ManagedBy   = "terraform"
  }
}

# Output the module resources
output "lambda_function_arn" {
  description = "ARN of the created Lambda function"
  value       = module.cloudwatch_logs_notifier.lambda_function_arn
}

output "sns_topic_arn" {
  description = "ARN of the created SNS topic"
  value       = module.cloudwatch_logs_notifier.sns_topic_arn
}

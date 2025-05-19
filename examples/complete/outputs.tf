output "lambda_function_arn" {
  description = "ARN of the created Lambda function"
  value       = module.cloudwatch_logs_notifier.lambda_function_arn
}

output "sns_topic_arn" {
  description = "ARN of the created SNS topic"
  value       = module.cloudwatch_logs_notifier.sns_topic_arn
}

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

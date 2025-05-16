output "lambda_function_arn" {
  description = "ARN of the created Lambda function"
  value       = module.cloudwatch_logs_notifier.lambda_function_arn
}

output "sns_topic_arn" {
  description = "ARN of the created SNS topic"
  value       = module.cloudwatch_logs_notifier.sns_topic_arn
}

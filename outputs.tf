output "lambda_function_name" {
  description = "The name of the Lambda function"
  value       = module.lambda_function.lambda_function_name
}

output "lambda_function_arn" {
  description = "The ARN of the Lambda function"
  value       = module.lambda_function.lambda_function_arn
}

output "lambda_function_invoke_arn" {
  description = "The invocation ARN of the Lambda function"
  value       = module.lambda_function.lambda_function_invoke_arn
}

output "cloudwatch_log_group_name" {
  description = "The name of the CloudWatch log group for the Lambda function"
  value       = module.lambda_function.lambda_cloudwatch_log_group_name
}

output "sns_topic_arn" {
  description = "The ARN of the SNS topic for CloudWatch log notifications"
  value       = module.sns.topic_arn
}

output "sns_topic_name" {
  description = "The name of the SNS topic for CloudWatch log notifications"
  value       = module.sns.topic_name
}

output "cloudwatch_alarm_sns_topic_arn" {
  description = "The ARN of the SNS topic for CloudWatch alarm notifications"
  value       = module.cloudwatch_alarm_sns.topic_arn
}

output "cloudwatch_alarm_sns_topic_name" {
  description = "The name of the SNS topic for CloudWatch alarm notifications"
  value       = module.cloudwatch_alarm_sns.topic_name
}

output "lambda_role_arn" {
  description = "The ARN of the IAM role used by the Lambda function"
  value       = module.lambda_function.lambda_role_arn
}

output "lambda_role_name" {
  description = "The name of the IAM role used by the Lambda function"
  value       = module.lambda_function.lambda_role_name
}


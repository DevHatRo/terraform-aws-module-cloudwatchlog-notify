variable "create_lambda_function" {
  description = "Whether to create the Lambda function"
  type        = bool
  default     = true
}

variable "enabled" {
  description = "Whether to enable all resources"
  type        = bool
  default     = true
}

variable "create_sns_topic" {
  description = "Whether to create the SNS topic"
  type        = bool
  default     = true
}

variable "create_cloudwatch_log_subscription_filter" {
  description = "Whether to create the CloudWatch log subscription filter"
  type        = bool
  default     = true
}

variable "function_name" {
  description = "The name of the Lambda function"
  type        = string
  default     = "cloudwatch-logs-notifier"
}

variable "cloudwatch_log_group_retention_in_days" {
  description = "The number of days to retain Lambda logs"
  type        = number
  default     = 14
}

variable "cloudwatch_log_group_kms_key_id" {
  description = "The ARN of the KMS Key to use when encrypting log data for Lambda"
  type        = string
  default     = null
}

variable "sns_topic_name" {
  description = "The name of the SNS topic for notifications"
  type        = string
  default     = "cloudwatch-logs-notifications"
}

variable "email_subscribers" {
  description = "List of email addresses to subscribe to the SNS topic"
  type        = list(string)
  default     = []
}

variable "log_group_subscriptions" {
  description = "List of CloudWatch log groups to subscribe to"
  type        = list(string)
  default     = []
}

variable "filter_pattern" {
  description = "The filter pattern to use for CloudWatch log subscriptions"
  type        = string
  default     = "{$.kubernetes.namespace_name = \"*\" && $.kubernetes.pod_name = \"*\" && $.kubernetes.container_name = \"*\" && $.log = \"*\"}"
}

variable "tags" {
  description = "A map of tags to apply to all resources"
  type        = map(string)
  default = {
    ManagedBy = "terraform"
  }
}

variable "additional_policy_statements" {
  description = "Additional IAM policy statements to attach to the Lambda function"
  type        = any
  default     = {}
}

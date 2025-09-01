#######################
# Lambda Function
#######################

module "lambda_function" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.1.0"

  create         = var.create_lambda_function && var.enabled
  function_name  = var.function_name
  description    = "CloudWatch Logs Notifier Lambda function"
  handler        = "lambda_function.lambda_handler"
  runtime        = "python3.13"
  timeout        = 30
  memory_size    = 128
  source_path    = "${path.module}/functions"
  create_package = true
  package_type   = "Zip"
  publish        = true

  environment_variables = {
    SNS_ARN           = module.sns.topic_arn
    ENABLE_SLACK      = var.enable_slack_notifications ? "true" : "false"
    SLACK_WEBHOOK_URL = var.slack_webhook_url
    SLACK_CHANNEL     = var.slack_channel
    SLACK_USERNAME    = var.slack_username
    EMAIL_SUBJECT     = var.email_subject
  }

  cloudwatch_logs_retention_in_days = var.cloudwatch_log_group_retention_in_days
  cloudwatch_logs_kms_key_id        = var.cloudwatch_log_group_kms_key_id

  attach_policy_statements = true
  policy_statements = merge(
    var.create_sns_topic && var.enabled ? {
      sns_publish = {
        effect    = "Allow",
        actions   = ["sns:Publish"],
        resources = [module.sns.topic_arn]
      }
    } : {},
    var.additional_policy_statements
  )

  allowed_triggers = merge(
    {
      CloudWatchLogs = {
        principal  = "logs.${data.aws_region.current.name}.amazonaws.com"
        source_arn = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:*"
      }
    },
    var.create_cloudwatch_alarm_sns_topic && var.enabled ? {
      CloudWatchAlarmSNS = {
        principal  = "sns.amazonaws.com"
        source_arn = module.cloudwatch_alarm_sns.topic_arn
      }
    } : {}
  )

  tags = var.tags
}

#######################
# SNS Topic for Notifications
#######################

module "sns" {
  source  = "terraform-aws-modules/sns/aws"
  version = "6.1.3"

  create       = var.create_sns_topic && var.enabled
  name         = var.sns_topic_name
  display_name = "CloudWatch Logs Error Notifications"

  subscriptions = {
    for idx, email in var.email_subscribers : "email-${idx}" => {
      protocol = "email"
      endpoint = email
    }
  }

  tags = var.tags
}

#######################
# SNS Topic for CloudWatch Alarms
#######################

module "cloudwatch_alarm_sns" {
  source  = "terraform-aws-modules/sns/aws"
  version = "6.1.3"

  create       = var.create_cloudwatch_alarm_sns_topic && var.enabled
  name         = var.cloudwatch_alarm_sns_topic_name
  display_name = "CloudWatch Alarm Notifications"

  # Subscribe the Lambda function to the SNS topic
  subscriptions = {
    lambda = {
      protocol = "lambda"
      endpoint = module.lambda_function.lambda_function_arn
    }
  }

  tags = var.tags
}

#######################
# CloudWatch Logs Subscription
#######################

resource "aws_cloudwatch_log_subscription_filter" "this" {
  count           = var.create_cloudwatch_log_subscription_filter && var.enabled ? length(var.log_group_subscriptions) : 0
  name            = "${var.function_name}-subscription-${count.index}"
  log_group_name  = var.log_group_subscriptions[count.index]
  filter_pattern  = var.filter_pattern
  destination_arn = module.lambda_function.lambda_function_arn
}

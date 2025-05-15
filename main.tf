terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.9"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.0"
    }
  }
}

provider "aws" {
  region = var.region
}

#######################
# Lambda Function
#######################

data "archive_file" "lambda_package" {
  type        = "zip"
  source_file = "${path.module}/functions/lambda_function.py"
  output_path = "${path.module}/functions/lambda_function.zip"
}

module "lambda_function" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 4.0"

  function_name = var.function_name
  description   = "CloudWatch Logs Notifier Lambda function"
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"
  timeout       = 30
  memory_size   = 128

  create_package         = false
  local_existing_package = data.archive_file.lambda_package.output_path

  environment_variables = {
    SNS_ARN = module.sns.topic_arn
  }

  cloudwatch_logs_retention_in_days = var.cloudwatch_log_group_retention_in_days
  cloudwatch_logs_kms_key_id        = var.cloudwatch_log_group_kms_key_id

  attach_policy_statements = true
  policy_statements = {
    sns_publish = {
      effect    = "Allow",
      actions   = ["sns:Publish"],
      resources = [module.sns.topic_arn]
    }
  }

  tags = var.tags
}

#######################
# SNS Topic
#######################

module "sns" {
  source  = "terraform-aws-modules/sns/aws"
  version = "~> 3.0"

  name         = var.sns_topic_name
  display_name = "CloudWatch Logs Error Notifications"
  tags         = var.tags
}

#######################
# CloudWatch Logs Subscription
#######################

resource "aws_cloudwatch_log_subscription_filter" "this" {
  count           = length(var.log_group_subscriptions)
  name            = "${var.function_name}-subscription-${count.index}"
  log_group_name  = var.log_group_subscriptions[count.index]
  filter_pattern  = var.filter_pattern
  destination_arn = module.sns.topic_arn

  depends_on = [aws_lambda_permission.cloudwatch_logs]
}

resource "aws_lambda_permission" "cloudwatch_logs" {
  count         = length(var.log_group_subscriptions)
  statement_id  = "AllowExecutionFromCloudWatchLogs${count.index}"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_function.lambda_function_name
  principal     = "logs.${var.region}.amazonaws.com"
  source_arn    = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:${var.log_group_subscriptions[count.index]}:*"
}

resource "aws_lambda_permission" "sns" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_function.lambda_function_name
  principal     = "sns.amazonaws.com"
  source_arn    = module.sns.topic_arn
}

resource "aws_sns_topic_subscription" "lambda" {
  topic_arn = module.sns.topic_arn
  protocol  = "lambda"
  endpoint  = module.lambda_function.lambda_function_arn
}

# Subscribe email addresses to SNS topic
resource "aws_sns_topic_subscription" "email" {
  count     = length(var.email_subscribers)
  topic_arn = module.sns.topic_arn
  protocol  = "email"
  endpoint  = var.email_subscribers[count.index]
}

#######################
# Data
#######################

data "aws_caller_identity" "current" {}

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

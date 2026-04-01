cat > modules/cloudwatch/main.tf << 'EOF'
variable "function_name" { type = string }
variable "prefix"        { type = string }

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.prefix}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Більше 10 помилок Lambda за 5 хвилин"
  dimensions = { FunctionName = var.function_name }
}

resource "aws_cloudwatch_dashboard" "analytics" {
  dashboard_name = "${var.prefix}-dashboard"
  dashboard_body = jsonencode({
    widgets = [
      { type = "metric", properties = { title = "Latency (ms)", period = 300, stat = "Average", metrics = [["Lab4/Analytics", "latency_ms"]] } },
      { type = "metric", properties = { title = "Request Count", period = 300, stat = "SampleCount", metrics = [["Lab4/Analytics", "latency_ms"]] } },
      { type = "metric", properties = { title = "Lambda Errors", period = 300, stat = "Sum", metrics = [["AWS/Lambda", "Errors", "FunctionName", var.function_name]] } }
    ]
  })
}
EOF
cat > envs/dev/main.tf << 'EOF'
provider "aws" {
  region = "eu-central-1"
}

locals {
  prefix       = "ivanishiv-olesia-06"
  logs_bucket  = "${local.prefix}-logs"
  cw_namespace = "Lab4/Analytics"
}

resource "aws_s3_bucket" "logs" {
  bucket        = local.logs_bucket
  force_destroy = true
}

resource "aws_s3_bucket_lifecycle_configuration" "logs_lifecycle" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "auto-cleanup"
    status = "Enabled"
    filter { prefix = "logs/" }
    transition {
      days          = 30
      storage_class = "GLACIER"
    }
    expiration {
      days = 365
    }
  }
}

module "backend" {
  source         = "../../modules/lambda"
  function_name  = "${local.prefix}-api-handler"
  source_file    = "${path.root}/../../src/app.py"
  s3_bucket_arn  = aws_s3_bucket.logs.arn
  s3_bucket_name = aws_s3_bucket.logs.id
  cw_namespace   = local.cw_namespace
}

module "api" {
  source               = "../../modules/api_gateway"
  api_name             = "${local.prefix}-http-api"
  lambda_invoke_arn    = module.backend.invoke_arn
  lambda_function_name = module.backend.function_name
}

module "monitoring" {
  source        = "../../modules/cloudwatch"
  prefix        = local.prefix
  function_name = module.backend.function_name
}

output "api_url" {
  value = module.api.api_endpoint
}

output "logs_bucket" {
  value = aws_s3_bucket.logs.id
}
EOF
terraform {
  # backend "s3" {
  #   bucket       = "tf-state-bucket-tb"
  #   key          = "backend/terraform.tfstate" # путь по которому кладет файл
  #   region       = "eu-north-1"
  #   encrypt      = true
  #   use_lockfile = true # раньше приходилось создавать отдельную таблицу в Dynamo DB
  # }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.29.0"
    }

  }
  required_version = "~> 1.14.3"
}

# Create S3 bucket
resource "aws_s3_bucket" "s3_tf_state" {
  bucket = "tf-state-bucket-tb"

  tags = {
    Name        = "S3 for tb tf-state"
    Environment = "Prod"
  }
}

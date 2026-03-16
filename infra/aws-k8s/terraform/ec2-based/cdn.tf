##### S3 Bucket #####
# Create S3 bucket
resource "aws_s3_bucket" "media" {
  bucket = "tb-media-files"

  # So tf destroy would work
  force_destroy = true

  tags = {
    Name = "S3 for tb tb media files"
  }
}

# Block all public access to bucket
resource "aws_s3_bucket_public_access_block" "media_block" {
  bucket = aws_s3_bucket.media.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "allow_cloudfront_policy" {
  bucket = aws_s3_bucket.media.id
  policy = data.aws_iam_policy_document.allow_cloudfront.json
}

# Политика, разрешающая чтение ТОЛЬКО этому дистрибутиву CloudFront
data "aws_iam_policy_document" "allow_cloudfront" {
  statement {
    sid       = "AllowCloudFrontServicePrincipalReadOnly"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.media.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      # ВНИМАНИЕ: Берем ARN из модуля!
      values = [module.cdn.cloudfront_distribution_arn]
    }
  }
}

##### CloudFront #####
module "cdn" {
  source  = "terraform-aws-modules/cloudfront/aws"
  version = "~> 6.4.0"

  comment         = "Trading Buddy Media CDN"
  enabled         = true
  is_ipv6_enabled = true
  price_class     = "PriceClass_100" # Самые дешевые регионы для экономии

  origin_access_control = {
    s3_oac = { # Это просто внутренний ключ для связки
      description      = "CloudFront access to S3"
      origin_type      = "s3"
      signing_behavior = "always"
      signing_protocol = "sigv4"
    }
  }

  # 2. Указываем наш бакет как источник данных
  origin = {
    media_bucket = { # Внутренний ключ источника
      domain_name           = aws_s3_bucket.media.bucket_regional_domain_name
      origin_access_control = "s3_oac" # Ссылаемся на ключ OAC из шага 1
    }
  }

  # 3. Настраиваем маршрутизацию запросов
  default_cache_behavior = {
    target_origin_id       = "media_bucket"      # Все запросы летят в ключ источника из шага 2
    viewer_protocol_policy = "redirect-to-https" # or allow-all

    allowed_methods = ["GET", "HEAD", "OPTIONS"]
    cached_methods  = ["GET", "HEAD"]

    # Стандартная политика кэширования AWS (CacheOptimized)
    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  }

  # 4. Сертификат по умолчанию (*.cloudfront.net)
  viewer_certificate = {
    cloudfront_default_certificate = true
  }
}



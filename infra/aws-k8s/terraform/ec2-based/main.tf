##### RDS #####
module "db" {
  source = "terraform-aws-modules/rds/aws"

  version = "~> 7.1.0"

  identifier = "tb-postgres-db"

  engine               = "postgresql"
  engine_version       = "17.0"
  family               = "postgres16"
  major_engine_version = "17"
  instance_class       = "db.t4g.micro"
  allocated_storage    = 5

  db_name  = "postgres"
  username = "avtorpetrovich"
  port     = "5432"

  multi_az               = false
  vpc_security_group_ids = [aws_security_group.rds_postgres.id]

  # DB subnet group
  create_db_subnet_group = true
  subnet_ids             = module.vpc.private_subnets

  maintenance_window = "Mon:00:00-Mon:03:00"
  backup_window      = "03:00-06:00"

  # So tf destroy would work
  backup_retention_period = 0
  skip_final_snapshot     = true
  deletion_protection     = false
}

##### EC2s #####
# AWS Systems Manager (SSM) Parameter Store
data "aws_ssm_parameter" "ecs_optimized_ami" {
  name = "/aws/service/ecs/optimized-ami/amazon-linux-2023/recommended/image_id"
}

### BACKEND ###
resource "aws_instance" "backend" {
  ami           = data.aws_ssm_parameter.ecs_optimized_ami.value
  instance_type = "t3g.micro"

  subnet_id = module.vpc.private_subnets[0]

  vpc_security_group_ids = [aws_security_group.backend.id] # нужна здесь даже если прописана у балансировщика для защиты от угроз изнутри подсети

  tags = {
    Name = "tb-backend-server-01"
  }
}

resource "aws_instance" "backend_listeners" {
  ami           = data.aws_ssm_parameter.ecs_optimized_ami.value
  instance_type = "t3g.micro"

  subnet_id = module.vpc.private_subnets[0]

  vpc_security_group_ids = [aws_security_group.backend.id]

  tags = {
    Name = "tb-backend-listeners-01"
  }
}

resource "aws_instance" "backend_poller" {
  ami           = data.aws_ssm_parameter.ecs_optimized_ami.value
  instance_type = "t3g.micro"

  subnet_id = module.vpc.private_subnets[0]

  vpc_security_group_ids = [aws_security_group.backend.id]

  tags = {
    Name = "tb-backend-poller-01"
  }
}

### FRONTEND ###
resource "aws_instance" "frontend" {
  ami           = data.aws_ssm_parameter.ecs_optimized_ami.value
  instance_type = "t3g.micro"

  subnet_id = module.vpc.private_subnets[0]

  vpc_security_group_ids = [aws_security_group.frontend.id]

  tags = {
    Name = "tb-frontend-server-01"
  }
}

##### SGs #####
# For internet-facing balancer
resource "aws_security_group" "public_alb" {
  name   = "tb-public-alb-sg"
  vpc_id = module.vpc.vpc_id


  # Accept all inbound HTTP traffic
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# For frontend
resource "aws_security_group" "frontend" {
  name   = "tb-frontend-ec2-sg"
  vpc_id = module.vpc.vpc_id

  ingress {
    from_port       = 3000 # Порт Frontend-серверов
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.public_alb.id] # принимает трафик только от публичного балансировщика
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# For internal balancer
resource "aws_security_group" "internal_alb" {
  name   = "tb-internal-alb-sg"
  vpc_id = module.vpc.vpc_id

  # Allow traffic only from frontend
  ingress {
    from_port       = 80
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.frontend.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# For backend server
resource "aws_security_group" "backend" {
  name   = "tb-backend-ec2-sg"
  vpc_id = module.vpc.vpc_id

  # Allow traffic only from internal ALB's Security Group
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.internal_alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# For RDS
resource "aws_security_group" "rds_postgres" {
  name        = "tb-rds-postgres-sg"
  description = "Allow PostgreSQL traffic from backend"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "Allow traffic ONLY from Backend EC2"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    # Only traffic from backend is allowed
    security_groups = [aws_security_group.backend.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

##### ALBs #####
module "public_alb" {
  source  = "terraform-aws-modules/alb/aws"
  version = "~> 10.5.0"

  name = "tb-public-alb"

  # ВОТ ГЛАВНЫЙ ПЕРЕКЛЮЧАТЕЛЬ:
  internal = false

  enable_deletion_protection = false

  # Указываем ПРИВАТНЫЕ подсети из модуля VPC
  subnets = module.vpc.public_subnets
  vpc_id  = module.vpc.vpc_id

  create_security_group = false                              # Отключаем дефолтную SG модуля
  security_groups       = [aws_security_group.public_alb.id] # Подключаем нашу

  listeners = {
    # Название произвольное
    http_80 = {
      port     = 80 # на каком порту балансировщик будет слушать
      protocol = "HTTP"
      forward = {
        target_group_key = "frontend_tg" # весь трафик пересылай на таргет группу под ключом frontend_tg
      }
    }
  }

  target_groups = {
    # Произвольное название таргет группы - нужно для связи с листенером
    frontend_tg = {
      name_prefix      = "front-" # префикс для Zero downtime
      backend_protocol = "HTTP"
      backend_port     = 3000       # Порт Frontend-серверов
      target_type      = "instance" # регистрация серверов по EC2 ID

      target_id = aws_instance.frontend.id

      health_check = {
        enabled             = true
        path                = "/health" # URL твоего приложения, который должен отдавать 200 OK
        port                = "8000"    # Обычно совпадает с backend_port
        protocol            = "HTTP"
        interval            = 30 # Как часто балансировщик будет пинговать сервер (в секундах)
        timeout             = 5  # Сколько секунд ждать ответа от сервера
        healthy_threshold   = 2  # Сколько успешных ответов нужно, чтобы признать сервер "Живым"
        unhealthy_threshold = 2  # Сколько ошибок нужно, чтобы признать сервер "Мертвым" и убрать с него трафик
      }
    }
  }
}

module "internal_alb" {
  source  = "terraform-aws-modules/alb/aws"
  version = "~> 10.5.0"

  name = "tb-internal-alb"

  # ВОТ ГЛАВНЫЙ ПЕРЕКЛЮЧАТЕЛЬ:
  internal = true

  enable_deletion_protection = false

  # Указываем ПРИВАТНЫЕ подсети из модуля VPC
  subnets = module.vpc.private_subnets
  vpc_id  = module.vpc.vpc_id

  create_security_group = false                                # Отключаем дефолтную SG
  security_groups       = [aws_security_group.internal_alb.id] # Подключаем нашу

  listeners = {
    http_8000 = {
      port     = 8000 # Фронтенд будет стучаться в балансировщик по 8000 порту
      protocol = "HTTP"
      forward = {
        target_group_key = "backend_tg"
      }
    }
  }

  target_groups = {
    backend_tg = {
      name_prefix      = "back-"
      backend_protocol = "HTTP"
      backend_port     = 8000 # Порт Backend-серверов
      target_type      = "instance"

      target_id = aws_instance.backend.id
      port      = 8000 # точечное переопределение таргет порта для данного сервера - опционально
    }
  }
}

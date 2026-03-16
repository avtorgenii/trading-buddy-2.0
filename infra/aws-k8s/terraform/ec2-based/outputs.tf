
# Достаем адрес базы данных
output "db_endpoint" {
  description = "Connection endpoint for the database"
  value       = module.db.db_instance_endpoint
}

# Достаем сгенерированный пароль
output "db_password" {
  description = "The generated database password"
  value       = jsondecode(data.aws_secretsmanager_secret_version.db_password.secret_string)["password"]
  sensitive   = true
}

# Читалка для секрета `terraform output -raw db_password`
data "aws_secretsmanager_secret_version" "db_password" {
  secret_id  = module.db.db_instance_master_user_secret_arn
  depends_on = [module.db]
}

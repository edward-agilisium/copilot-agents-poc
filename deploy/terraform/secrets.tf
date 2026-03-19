resource "aws_secretsmanager_secret" "copilot_config" {
  name                    = "copilot-agent/config"
  description             = "Copilot Agent application secrets"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "copilot_config" {
  secret_id = aws_secretsmanager_secret.copilot_config.id

  secret_string = jsonencode({
    TENANT_ID     = var.tenant_id
    CLIENT_ID     = var.client_id
    CLIENT_SECRET = var.client_secret
    DRIVE_ID      = var.drive_id
    VDB_URL       = var.vdb_url
    VDB_API       = var.vdb_api
  })
}

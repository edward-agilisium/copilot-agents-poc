output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.copilot_agent.id
}

output "public_ip" {
  description = "Elastic IP address of the EC2 instance"
  value       = aws_eip.copilot_agent.public_ip
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i copilot-agent-key.pem ec2-user@${aws_eip.copilot_agent.public_ip}"
}

output "secrets_arn" {
  description = "ARN of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.copilot_config.arn
}

output "webhook_url" {
  description = "SharePoint webhook notification URL"
  value       = "https://${aws_eip.copilot_agent.public_ip}/webhook"
}

output "app_url" {
  description = "Application URL"
  value       = "https://${aws_eip.copilot_agent.public_ip}"
}

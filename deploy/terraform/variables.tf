variable "aws_region" {
  description = "AWS region for all resources"
  default     = "us-west-2"
}

variable "aws_profile" {
  description = "AWS CLI profile name to use"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  default     = "t3.medium"
}

variable "my_ip" {
  description = "Your IP address for SSH access (e.g. 203.0.113.10/32)"
  type        = string
}

variable "repo_url" {
  description = "Git repository URL to clone on the EC2 instance"
  type        = string
}

variable "tenant_id" {
  description = "Azure AD Tenant ID"
  type        = string
  sensitive   = true
}

variable "client_id" {
  description = "Azure AD Client ID"
  type        = string
  sensitive   = true
}

variable "client_secret" {
  description = "Azure AD Client Secret"
  type        = string
  sensitive   = true
}

variable "drive_id" {
  description = "SharePoint Drive ID"
  type        = string
  sensitive   = true
}

variable "vdb_url" {
  description = "Qdrant Cloud URL"
  type        = string
  sensitive   = true
}

variable "vdb_api" {
  description = "Qdrant Cloud API Key"
  type        = string
  sensitive   = true
}

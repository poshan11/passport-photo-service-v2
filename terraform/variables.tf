variable "project_id" {
  type        = string
  description = "Google Cloud project ID."
}

variable "region" {
  type        = string
  description = "Primary region for Cloud Run, GCS, and Artifact Registry."
  default     = "us-central1"
}

variable "service_name" {
  type        = string
  description = "Cloud Run service name."
}

variable "bucket_name" {
  type        = string
  description = "GCS bucket for processed photo storage."
}

variable "bucket_force_destroy" {
  type        = bool
  description = "Allow bucket deletion even when objects exist."
  default     = false
}

variable "bucket_versioning_enabled" {
  type        = bool
  description = "Enable object versioning on the photo bucket."
  default     = true
}

variable "db_instance_name" {
  type        = string
  description = "Cloud SQL instance name."
}

variable "db_zone" {
  type        = string
  description = "Cloud SQL zone in the selected region."
  default     = "us-central1-c"
}

variable "db_version" {
  type        = string
  description = "Cloud SQL database version."
  default     = "MYSQL_8_0"
}

variable "db_tier" {
  type        = string
  description = "Cloud SQL instance machine tier."
  default     = "db-custom-1-3840"
}

variable "sql_edition" {
  type        = string
  description = "Cloud SQL edition to avoid provider drift (e.g. ENTERPRISE)."
  default     = "ENTERPRISE"
}

variable "db_disk_size_gb" {
  type        = number
  description = "Cloud SQL disk size in GB."
  default     = 20
}

variable "secret_env_vars" {
  type        = map(string)
  description = "Temporary single source for app secrets: map of Cloud Run env var name -> secret value. Terraform creates/updates Secret Manager secrets + versions and injects them into Cloud Run. Warning: values are still stored in Terraform state."
  default     = {}
  sensitive   = true
}

variable "secret_env_secret_ids" {
  type        = map(string)
  description = "Preferred final mode: map of Cloud Run env var name -> existing Secret Manager secret_id. Terraform only binds these secrets to Cloud Run/IAM and does not manage values."
  default     = {}
}

variable "sql_backups_enabled" {
  type        = bool
  description = "Enable automated backups for Cloud SQL."
  default     = true
}

variable "sql_deletion_protection" {
  type        = bool
  description = "Protect Cloud SQL instance from deletion."
  default     = true
}

variable "database_name" {
  type        = string
  description = "Application database name."
}

variable "db_user" {
  type        = string
  description = "Application database user."
}

variable "db_password" {
  type        = string
  description = "Application database password (legacy/plain mode). Prefer db_password_secret_id for runtime and SQL user provisioning."
  default     = ""
  sensitive   = true
}

variable "db_password_secret_id" {
  type        = string
  description = "Existing Secret Manager secret_id for DB_PASSWORD. If set, Cloud Run reads DB_PASSWORD from Secret Manager and Terraform can also use it for the Cloud SQL user password."
  default     = ""
}

variable "db_password_secret_version" {
  type        = string
  description = "Secret Manager version for db_password_secret_id (use latest unless pinning intentionally)."
  default     = "latest"
}

variable "artifact_registry_repository_id" {
  type        = string
  description = "Artifact Registry repository ID. Leave empty to auto-generate from service_name."
  default     = ""
}

variable "container_image" {
  type        = string
  description = "Prebuilt container image URI. Leave empty to use Artifact Registry image generated from project/region/service_name."
  default     = ""
}

variable "image_tag" {
  type        = string
  description = "Container image tag used when container_image is not set."
  default     = "latest"
}

variable "build_container_image" {
  type        = bool
  description = "Build and push the image from the local repo using Cloud Build during terraform apply."
  default     = false
}

variable "source_build_nonce" {
  type        = string
  description = "Change this value to force a rebuild when build_container_image=true."
  default     = ""
}

variable "container_port" {
  type        = number
  description = "Container port exposed by the Flask/Gunicorn app."
  default     = 5001
}

variable "cloud_run_cpu" {
  type        = string
  description = "Cloud Run CPU limit (e.g. 1, 2)."
  default     = "2"
}

variable "cloud_run_memory" {
  type        = string
  description = "Cloud Run memory limit (e.g. 1Gi, 2Gi)."
  default     = "2Gi"
}

variable "cloud_run_timeout_seconds" {
  type        = number
  description = "Cloud Run request timeout in seconds."
  default     = 300
}

variable "cloud_run_min_instances" {
  type        = number
  description = "Minimum number of Cloud Run instances."
  default     = 0
}

variable "cloud_run_max_instances" {
  type        = number
  description = "Maximum number of Cloud Run instances."
  default     = 5
}

variable "allow_unauthenticated" {
  type        = bool
  description = "Allow public unauthenticated access to Cloud Run."
  default     = true
}

variable "promo_mode_enabled" {
  type        = bool
  description = "Enable temporary promo mode pricing in backend responses and order processing."
  default     = false
}

variable "promo_digital_only" {
  type        = bool
  description = "When promo mode is enabled, limit promo to digital flow only (frontend can hide pickup/shipping)."
  default     = true
}

variable "promo_banner_text" {
  type        = string
  description = "Promo banner text returned by /getCost for frontend display."
  default     = "Limited-time free digital passport photo"
}

variable "enable_custom_domain_mapping" {
  type        = bool
  description = "Create a Cloud Run custom domain mapping for the service."
  default     = false
}

variable "custom_domain_name" {
  type        = string
  description = "Custom domain/subdomain to map to Cloud Run (e.g. api.example.com)."
  default     = ""
}

variable "import_sql_dump" {
  type        = bool
  description = "Upload and import a local SQL dump into Cloud SQL using gcloud during terraform apply."
  default     = false
}

variable "sql_dump_local_path" {
  type        = string
  description = "Local path to the SQL dump file to import. Required when import_sql_dump=true."
  default     = ""
}

variable "sql_dump_object_name" {
  type        = string
  description = "Object path inside the storage bucket for the SQL dump upload. Leave empty to auto-generate."
  default     = ""
}

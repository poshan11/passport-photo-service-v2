output "cloud_run_service_url" {
  description = "Public URL for the Cloud Run service."
  value       = google_cloud_run_v2_service.app.uri
}

output "cloud_run_service_name" {
  value = google_cloud_run_v2_service.app.name
}

output "storage_bucket_name" {
  value = google_storage_bucket.photos.name
}

output "sql_instance_connection_name" {
  value = google_sql_database_instance.default.connection_name
}

output "sql_instance_name" {
  value = google_sql_database_instance.default.name
}

output "container_image_uri" {
  value = local.container_image
}

output "custom_domain_name" {
  description = "Configured custom domain (if enabled)."
  value       = try(google_cloud_run_domain_mapping.custom[0].name, "")
}

output "custom_domain_dns_records" {
  description = "DNS records to create at your registrar for the custom domain mapping (if enabled)."
  value       = try(google_cloud_run_domain_mapping.custom[0].status[0].resource_records, [])
}

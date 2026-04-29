locals {
  artifact_repository_id         = var.artifact_registry_repository_id != "" ? var.artifact_registry_repository_id : "${var.service_name}-images"
  container_image                = var.container_image != "" ? var.container_image : "${var.region}-docker.pkg.dev/${var.project_id}/${local.artifact_repository_id}/${var.service_name}:${var.image_tag}"
  sql_dump_basename              = var.sql_dump_local_path != "" ? basename(var.sql_dump_local_path) : "dump.sql"
  sql_dump_object_name           = var.sql_dump_object_name != "" ? var.sql_dump_object_name : "db-dumps/${local.sql_dump_basename}"
  managed_secret_env_names       = toset(keys(nonsensitive(var.secret_env_vars)))
  external_secret_env_names      = toset(keys(var.secret_env_secret_ids))
  db_password_is_secret          = var.db_password_secret_id != ""
  external_secret_iam_secret_ids = toset(distinct(values(var.secret_env_secret_ids)))
}

data "google_project" "current" {
  project_id = var.project_id
}

data "google_secret_manager_secret_version" "db_password" {
  count = local.db_password_is_secret ? 1 : 0

  project = var.project_id
  secret  = var.db_password_secret_id
  version = var.db_password_secret_version
}

resource "google_project_service" "required" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "sqladmin.googleapis.com",
    "storage.googleapis.com",
  ])

  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_storage_bucket" "photos" {
  name                        = var.bucket_name
  location                    = var.region
  project                     = var.project_id
  force_destroy               = var.bucket_force_destroy
  uniform_bucket_level_access = true

  versioning {
    enabled = var.bucket_versioning_enabled
  }

  depends_on = [google_project_service.required]
}

resource "google_storage_bucket_object" "db_dump" {
  count = var.import_sql_dump && var.sql_dump_local_path != "" ? 1 : 0

  name   = local.sql_dump_object_name
  bucket = google_storage_bucket.photos.name
  source = var.sql_dump_local_path
}

resource "google_storage_bucket_iam_member" "cloud_sql_import_reader" {
  count = var.import_sql_dump ? 1 : 0

  bucket = google_storage_bucket.photos.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-cloud-sql.iam.gserviceaccount.com"
}

resource "google_sql_database_instance" "default" {
  name                = var.db_instance_name
  project             = var.project_id
  region              = var.region
  database_version    = var.db_version
  deletion_protection = var.sql_deletion_protection

  settings {
    edition                     = var.sql_edition
    tier                        = var.db_tier
    disk_size                   = var.db_disk_size_gb
    disk_autoresize             = true
    availability_type           = "ZONAL"
    deletion_protection_enabled = var.sql_deletion_protection

    backup_configuration {
      enabled = var.sql_backups_enabled
    }

    ip_configuration {
      ipv4_enabled = true
    }

    location_preference {
      zone = var.db_zone
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_sql_database" "app" {
  name     = var.database_name
  project  = var.project_id
  instance = google_sql_database_instance.default.name
}

resource "google_sql_user" "app" {
  name     = var.db_user
  project  = var.project_id
  instance = google_sql_database_instance.default.name
  password = local.db_password_is_secret ? data.google_secret_manager_secret_version.db_password[0].secret_data : var.db_password
}

resource "google_service_account" "run_sa" {
  project      = var.project_id
  account_id   = substr(replace("${var.service_name}-sa", "_", "-"), 0, 30)
  display_name = "${var.service_name} Cloud Run service account"
}

resource "google_project_iam_member" "run_sa_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.run_sa.email}"
}

resource "google_storage_bucket_iam_member" "run_sa_bucket_admin" {
  bucket = google_storage_bucket.photos.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.run_sa.email}"
}

resource "google_service_account_iam_member" "run_sa_token_creator_self" {
  service_account_id = google_service_account.run_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.run_sa.email}"
}

resource "google_secret_manager_secret" "app" {
  for_each = local.managed_secret_env_names

  project   = var.project_id
  secret_id = substr(replace(lower(each.value), "_", "-"), 0, 255)

  replication {
    auto {}
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_version" "app" {
  for_each = local.managed_secret_env_names

  secret      = google_secret_manager_secret.app[each.value].id
  secret_data = var.secret_env_vars[each.value]
}

resource "google_secret_manager_secret_iam_member" "run_sa_access" {
  for_each = local.managed_secret_env_names

  project   = var.project_id
  secret_id = google_secret_manager_secret.app[each.value].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.run_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "run_sa_access_existing" {
  for_each = local.external_secret_iam_secret_ids

  project   = var.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.run_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "run_sa_access_db_password" {
  count = local.db_password_is_secret ? 1 : 0

  project   = var.project_id
  secret_id = var.db_password_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.run_sa.email}"
}

resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.region
  repository_id = local.artifact_repository_id
  description   = "Container images for ${var.service_name}"
  format        = "DOCKER"

  depends_on = [google_project_service.required]
}

resource "terraform_data" "build_container_image" {
  count = var.build_container_image ? 1 : 0

  triggers_replace = {
    image_uri      = local.container_image
    source_nonce   = var.source_build_nonce
    dockerfile_sha = fileexists("${path.module}/../Dockerfile") ? filesha256("${path.module}/../Dockerfile") : ""
    reqs_sha       = fileexists("${path.module}/../requirements.txt") ? filesha256("${path.module}/../requirements.txt") : ""
  }

  provisioner "local-exec" {
    working_dir = "${path.module}/.."
    command     = "gcloud builds submit --project=${var.project_id} --tag=${local.container_image} ."
  }

  depends_on = [google_artifact_registry_repository.images]
}

resource "google_cloud_run_v2_service" "app" {
  name     = var.service_name
  project  = var.project_id
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.run_sa.email
    timeout         = "${var.cloud_run_timeout_seconds}s"

    scaling {
      min_instance_count = var.cloud_run_min_instances
      max_instance_count = var.cloud_run_max_instances
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.default.connection_name]
      }
    }

    containers {
      image = local.container_image

      ports {
        container_port = var.container_port
      }

      resources {
        limits = {
          cpu    = var.cloud_run_cpu
          memory = var.cloud_run_memory
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      env {
        name  = "INSTANCE_CONNECTION_NAME"
        value = google_sql_database_instance.default.connection_name
      }

      env {
        name  = "DB_USER"
        value = var.db_user
      }

      dynamic "env" {
        for_each = local.db_password_is_secret ? [1] : []
        content {
          name = "DB_PASSWORD"
          value_source {
            secret_key_ref {
              secret  = var.db_password_secret_id
              version = var.db_password_secret_version
            }
          }
        }
      }

      dynamic "env" {
        for_each = local.db_password_is_secret ? [] : [1]
        content {
          name  = "DB_PASSWORD"
          value = var.db_password
        }
      }

      env {
        name  = "DB_NAME"
        value = var.database_name
      }

      env {
        name  = "STORAGE_BUCKET"
        value = google_storage_bucket.photos.name
      }

      env {
        name  = "PROMO_MODE_ENABLED"
        value = tostring(var.promo_mode_enabled)
      }

      env {
        name  = "PROMO_DIGITAL_ONLY"
        value = tostring(var.promo_digital_only)
      }

      env {
        name  = "PROMO_HIDE_FULFILLMENT_OPTIONS"
        value = tostring(var.promo_digital_only)
      }

      env {
        name  = "PROMO_BANNER_TEXT"
        value = var.promo_banner_text
      }

      # Force a fresh Cloud Run revision when needed without changing behavior.
      env {
        name  = "DEPLOY_NONCE"
        value = var.source_build_nonce
      }

      dynamic "env" {
        for_each = local.managed_secret_env_names
        content {
          name = env.value

          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.app[env.value].secret_id
              version = "latest"
            }
          }
        }
      }

      dynamic "env" {
        for_each = local.external_secret_env_names
        content {
          name = env.value

          value_source {
            secret_key_ref {
              secret  = var.secret_env_secret_ids[env.value]
              version = "latest"
            }
          }
        }
      }
    }
  }

  depends_on = [
    google_project_iam_member.run_sa_cloudsql_client,
    google_storage_bucket_iam_member.run_sa_bucket_admin,
    google_service_account_iam_member.run_sa_token_creator_self,
    google_secret_manager_secret_version.app,
    google_secret_manager_secret_iam_member.run_sa_access,
    google_secret_manager_secret_iam_member.run_sa_access_existing,
    google_secret_manager_secret_iam_member.run_sa_access_db_password,
    google_sql_database.app,
    google_sql_user.app,
    terraform_data.build_container_image,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  count = var.allow_unauthenticated ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_domain_mapping" "custom" {
  count = var.enable_custom_domain_mapping && var.custom_domain_name != "" ? 1 : 0

  location = var.region
  name     = var.custom_domain_name

  metadata {
    namespace = var.project_id
  }

  spec {
    route_name = google_cloud_run_v2_service.app.name
  }

  depends_on = [google_cloud_run_v2_service.app]
}

resource "terraform_data" "import_sql_dump" {
  count = var.import_sql_dump && var.sql_dump_local_path != "" ? 1 : 0

  triggers_replace = {
    instance         = google_sql_database_instance.default.name
    database         = google_sql_database.app.name
    object_name      = google_storage_bucket_object.db_dump[0].name
    object_md5       = google_storage_bucket_object.db_dump[0].md5hash
    import_on_change = tostring(var.import_sql_dump)
  }

  provisioner "local-exec" {
    command = "gcloud sql import sql ${google_sql_database_instance.default.name} gs://${google_storage_bucket.photos.name}/${google_storage_bucket_object.db_dump[0].name} --project=${var.project_id} --database=${google_sql_database.app.name} --quiet"
  }

  depends_on = [
    google_sql_database.app,
    google_sql_user.app,
    google_storage_bucket_object.db_dump,
    google_storage_bucket_iam_member.cloud_sql_import_reader,
  ]
}

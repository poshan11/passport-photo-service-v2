# Terraform deployment

This Terraform config provisions the GCP infrastructure for the passport photo backend:

- Cloud Run service for the Flask backend
- Cloud Storage bucket for processed photos
- Cloud SQL (MySQL) instance, database, and app user
- Artifact Registry repository for container images
- Secret Manager secrets and Cloud Run secret env bindings
- Optional Cloud Run custom domain mapping (stable API URL)
- Optional local image build/push using Cloud Build during `terraform apply`
- Optional SQL dump upload/import during `terraform apply`

## Prerequisites

- Terraform `>= 1.5`
- `gcloud` CLI installed and authenticated (`gcloud auth login` and `gcloud auth application-default login`)
- Billing enabled on the target GCP project

## One-time setup

1. Copy `terraform.tfvars.example` to `terraform.tfvars`
2. Fill in your project, bucket, DB, and SQL dump path values
3. Choose how secrets are managed:
   - **Quick start:** put sensitive values directly in `secret_env_vars = { ... }` in `terraform.tfvars`
   - **Recommended for production:** manage secrets in Secret Manager out-of-band and bind by name via `secret_env_secret_ids = { ... }` (Terraform state never contains the raw values)
4. Decide image strategy:
   - Set `build_container_image = true` to build from this repo during apply, or
   - Provide `container_image` for an already-pushed image

## Deploy

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## Stable API URL with a custom domain (optional)

Raw Cloud Run URLs (`*.run.app`) change when you move projects. To keep the API URL stable, use a custom domain such as `api.yourdomain.com`.

### One-time manual steps

1. Verify ownership of `yourdomain.com` in Google Search Console under the target GCP account/project
2. Enable custom domain mapping in `terraform.tfvars`:

```hcl
enable_custom_domain_mapping = true
custom_domain_name           = "api.yourdomain.com"
```

3. Run `terraform apply`
4. Copy DNS records from Terraform output `custom_domain_dns_records`
5. Add those DNS records at your DNS provider
6. Wait for certificate provisioning to complete

After that, point the frontend at `https://api.yourdomain.com`. Moving GCP projects later only requires recreating the mapping and updating DNS — the frontend URL stays the same.

## Notes

- SQL import uses `gcloud sql import sql` via a `local-exec` step because the Google Terraform provider has no first-class SQL dump import resource.
- Cloud Run env vars passed by Terraform match `config.py` (`INSTANCE_CONNECTION_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `STORAGE_BUCKET`).
- `secret_env_vars` values are stored in Secret Manager and injected into Cloud Run as environment variables, but the values still land in Terraform state. For production, prefer `secret_env_secret_ids` so Terraform only references secret *names*.
- `DB_PASSWORD` can be migrated to Secret Manager via `db_password_secret_id`.
- If `build_container_image = true`, bump `source_build_nonce` to force a rebuild on the next apply.
- Cloud SQL `edition` is pinned to avoid provider drift.
- Custom domain mapping creation will fail until domain ownership is verified in Search Console and DNS records are in place.

## Smoke test the deployed service

```bash
./scripts/smoke_test_cloud_run.sh --base-url https://YOUR_CLOUD_RUN_URL --full-order-flow
```

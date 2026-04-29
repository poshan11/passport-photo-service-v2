# Passport Photo Service

Production backend for an iOS passport-photo app — solo-built, live in the App Store, AI-pair-programmed.

> **Live app:** [Passport Photo, ID Photo on the App Store](https://apps.apple.com/us/app/passport-photo-id-photo/id6748840005)
> **Stack:** Python · Flask · MODNet · Cloud Run · Cloud SQL · Terraform · Stripe · PayPal · Apple IAP

This repo is the **server side** of a real, paying iOS product. It accepts a user-uploaded selfie, runs ML-driven background removal + face-landmark detection, generates a country-compliant passport photo (US, Canada, UK, India, EU Schengen, baby passport, plus arbitrary custom sizes), composes a 4×6 print sheet, and delivers it via in-app digital download or via order placement to Walgreens for in-store pickup.

---

## Why this repo is interesting

- **End-to-end ownership.** I designed, built, deployed, and operate it solo: ML pipeline, REST API, IaC, payments (Stripe + PayPal + Apple IAP), transactional email, third-party fulfillment integration, observability, on-call.
- **Live commercial product.** Not a tutorial clone. Real users, real Stripe charges, real Cloud SQL, real Cloud Run revisions.
- **AI-native development workflow.** Built with Claude Code as a pair-programming partner — see *[Built with AI pair programming](#built-with-ai-pair-programming)* below for what that actually looked like in practice.
- **Production-grade infra.** Terraform-managed GCP project, Secret Manager bindings, Cloud Run with custom domain mapping, automated SQL dump import, smoke-test scripts, gunicorn `--preload` to amortize model load across workers, gzip JSON responses, async email + GCS offload.

---

## Architecture

```
┌──────────────┐    HTTPS    ┌──────────────────────────┐
│  iOS app     │  ────────▶  │  Cloud Run (Flask)       │
│ (React       │             │   /process               │
│  Native)     │  ◀────────  │   /createOrder           │
└──────────────┘             │   /getCost  /healthz     │
                             │   /paypal/* /stripe/*    │
                             └──┬───────┬──────────┬────┘
                                │       │          │
                  ┌─────────────┘       │          └────────────┐
                  ▼                     ▼                       ▼
          ┌──────────────┐    ┌────────────────────┐   ┌──────────────────┐
          │ Cloud SQL    │    │ Cloud Storage      │   │ External APIs    │
          │ (MySQL)      │    │ (processed photos, │   │ Stripe, PayPal,  │
          │ orders,      │    │ composites)        │   │ Walgreens, MS    │
          │ referrals    │    │                    │   │ Graph (email)    │
          └──────────────┘    └────────────────────┘   └──────────────────┘

Inside Cloud Run, per request:
  selfie ─▶ MODNet (alpha matting) ─▶ face_recognition (68-pt landmarks)
        ─▶ dynamic crop (eye-line, head-ratio, chin padding per doc spec)
        ─▶ resize to country dimensions (300dpi) ─▶ composite 4×6 print sheet
        ─▶ upload to GCS ─▶ return signed URLs
```

## Tech stack

| Layer | Tools |
|---|---|
| **Runtime** | Python 3, Flask, gunicorn (`--preload`, 4 workers, 120s timeout), `flask-compress` for gzip JSON |
| **ML** | [MODNet](https://github.com/ZHKKKe/MODNet) for background removal · `face_recognition` (HOG/CNN dlib) for landmarks · OpenCV + PIL for compositing |
| **Storage** | Cloud SQL (MySQL), Cloud Storage (signed URLs) |
| **Payments** | Stripe (cards + webhooks), PayPal (sandbox + live), Apple IAP receipt validation |
| **Email** | Microsoft Graph API for transactional sends, SMTP fallback |
| **Fulfillment** | Walgreens print API (in-store pickup) · Browser-Use for headless Google Photos / Walmart upload automation |
| **Infra** | GCP Cloud Run, Cloud Build, Artifact Registry, Secret Manager, custom-domain mapping; **Terraform** for everything |
| **Frontend** (separate repo) | React Native + Expo |

## Endpoints (highlights)

| Endpoint | What it does |
|---|---|
| `POST /process` | Upload selfie → returns processed image token |
| `GET /preview/<token>` | Preview the processed photo before paying |
| `POST /change-background` | Re-render the same photo with a different background color |
| `POST /createOrder` | Create order, charge Stripe/PayPal, send confirmation email, kick off fulfillment |
| `POST /stripe/webhook` | Handle Stripe `payment_intent.succeeded` etc. |
| `GET /getCost` | Quote pricing + active promo flags (used by frontend at launch) |
| `GET /_ah/health`, `/healthz` | Readiness probes for Cloud Run + uptime monitoring |

## Local development

```bash
# 1. Clone
git clone https://github.com/<you>/passport-photo-service.git
cd passport-photo-service

# 2. Python deps
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. MODNet model weights (not redistributed — pull from upstream)
git clone https://github.com/ZHKKKe/MODNet.git
# Then download modnet_photographic_portrait_matting.ckpt from the MODNet repo
# and place it at MODNet/ckpt/modnet_photographic_portrait_matting.ckpt

# 4. Config
cp .env.example .env   # then fill in DB, GCS, Stripe, etc.
export $(cat .env | xargs)

# 5. Run
python apis.py
# or
gunicorn -w 4 --preload --timeout 120 -b 0.0.0.0:5001 apis:app
```

## Deploy to your own GCP project

The full GCP project — Cloud Run service, Cloud SQL instance, Cloud Storage bucket, Artifact Registry repo, Secret Manager secrets, optional custom-domain mapping — is provisioned by Terraform.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # fill in your values
terraform init
terraform apply
```

See [`terraform/README.md`](terraform/README.md) for the secret-handling options (raw values vs. Secret Manager bind-by-name) and the custom-domain setup.

## Built with AI pair programming

This codebase was built solo, but I was rarely the only one in the room.

I used **Claude Code** (the Anthropic CLI agent) as a daily-driver pair programmer through every phase of this product:

- **Architecture conversations** — sketched the request lifecycle, the Cloud Run + Cloud SQL + GCS topology, the failure modes of synchronous vs. async fulfillment, and the trade-offs of running MODNet in-process vs. behind a separate model server. The decision to keep MODNet in the Flask process (with gunicorn `--preload` so weights are loaded once and inherited across workers) came out of one of those conversations.
- **Prompt-engineered subsystems end-to-end** — the dynamic-crop geometry logic in `utils/process_images.py` (eye-line ratios, head-to-frame ratios, chin padding per country spec) was iterated on with the LLM as a math/CV reviewer, not a code generator. I'd describe the failure mode I was seeing on a real test image, paste the offending output, and we'd refine the formula together.
- **Agent-driven third-party integration** — the Walgreens print fulfillment integration and the Walmart / Google Photos upload paths were prototyped with the help of [Browser-Use](https://github.com/browser-use/browser-use) (LLM-driven browser automation) before I knew if first-party APIs even existed for the flow I needed. That let me validate the user experience end-to-end in days, then swap in the real REST API once I had a working spec.
- **Code review on every PR** — every non-trivial change was reviewed by an LLM before merge. Catches I remember: a missing `with` context manager around a torch tensor that was leaking GPU memory, a Stripe webhook handler that wasn't idempotent, a face-detection pre-downscale that should have been gated on input resolution.
- **Infra-as-code authoring** — the Terraform module (Cloud Run, Cloud SQL, custom domain mapping with manual ownership-verification gating, Secret Manager secrets bound by name, Artifact Registry, etc.) was authored in a long iterative session with Claude — I described the deployment shape I wanted, it produced HCL, I applied + broke + iterated.
- **Decision logs and feedback memory** — I keep persistent project notes that the LLM reads at the start of each session, so context like *"composite generation is required even for digital orders, because users still want to print 4 copies themselves"* survives across days. That feedback memory is the difference between an assistant that helps and one that constantly re-introduces yesterday's bugs.

The result is a real, deployed, paying-customer product I built alone in a few months — at a velocity that would not have been possible without aggressive use of LLM tooling. I think this is the shape of how senior engineers will work; I wanted to demonstrate I'm already doing it.

## Repo layout

```
.
├── apis.py                      # Flask app, all REST endpoints
├── config.py                    # 12-factor config, all values from env
├── walgreens_api.py             # Print fulfillment integration
├── google_photos_automation.py  # Headless Google Photos upload helper
├── gcs_to_photos.py             # GCS → Google Photos sync utility
├── debug_face_detection.py      # CLI for trying multiple face detectors on a single image
├── test_document_mappings.py    # Unit tests for country crop configs
├── tests/
│   └── test_live_cloud_run_api.py  # Post-deploy live integration test
├── utils/
│   ├── process_images.py        # MODNet + face_recognition + dynamic crop pipeline
│   ├── storage_utils.py         # GCS upload/download wrappers
│   ├── database.py              # MySQL connection pool, repositories
│   ├── order_utils.py           # Order/payment state machine
│   ├── orderconfirmationemail.py# MS Graph + email composition
│   ├── browser_use_automation.py# LLM-driven browser-automation tasks
│   ├── api_responses.py         # Response envelope helpers
│   ├── error_handler.py         # Flask error handlers
│   └── generic_utils.py         # Shared helpers
├── scripts/
│   └── smoke_test_cloud_run.sh  # Post-deploy smoke check
├── terraform/                   # GCP infra-as-code (Cloud Run, SQL, GCS, …)
├── Dockerfile
├── requirements.txt
├── create_referrals_table.sql   # Referrals table DDL
└── frontend_doc_config_example.js # Example doc-config payload from mobile app
```

## License

MIT — see [LICENSE](LICENSE).

The MODNet model weights are licensed separately by their authors and are **not redistributed** in this repo.

---

## About me

I'm Poshan Bastola — distributed-systems engineer, ~5 years on the Object Storage Platform at Oracle Cloud Infrastructure (exabyte-scale, fleet capacity / observability / data pipelines). This repo is one of the things I've been building since.

[LinkedIn](https://linkedin.com/in/poshan-bastola) · [App Store](https://apps.apple.com/us/app/passport-photo-id-photo/id6748840005)

#!/usr/bin/env bash
set -euo pipefail

BASE_URL=""
IMAGE_PATH="${HOME}/Downloads/fotor-ai-20250301175637.jpg"
FULL_ORDER_FLOW=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      BASE_URL="$2"; shift 2 ;;
    --image-path)
      IMAGE_PATH="$2"; shift 2 ;;
    --full-order-flow)
      FULL_ORDER_FLOW=true; shift ;;
    --help|-h)
      cat <<USAGE
Usage: $(basename "$0") --base-url URL [--image-path PATH] [--full-order-flow]
USAGE
      exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$BASE_URL" ]]; then
  echo "--base-url is required" >&2
  exit 1
fi

BASE_URL="${BASE_URL%/}"

echo "[smoke] GET ${BASE_URL}/getCost"
get_cost_status="$(curl -sS -o /tmp/getcost_smoke_body.json -w '%{http_code}' "${BASE_URL}/getCost")"
cat /tmp/getcost_smoke_body.json
printf '\n'
if [[ "$get_cost_status" != "200" ]]; then
  echo "[smoke] /getCost failed with HTTP ${get_cost_status}" >&2
  exit 1
fi

if [[ "$FULL_ORDER_FLOW" == true ]]; then
  if [[ ! -f "$IMAGE_PATH" ]]; then
    echo "[smoke] image not found for full flow: $IMAGE_PATH" >&2
    exit 1
  fi

  echo "[smoke] Running full live API flow test"
  LIVE_API_BASE_URL="$BASE_URL" \
  LIVE_API_IMAGE_PATH="$IMAGE_PATH" \
  python3 -m unittest discover -s tests -p 'test_live_cloud_run_api.py' -v
fi

echo "[smoke] OK"

#!/usr/bin/env bash
# ------------------------------------------------------------
# Proyecto HVS – container entrypoint (v2)
# ------------------------------------------------------------
#  • Re-hydrates Google service-account JSON
#    from dashboard environment variables (raw or base-64).
#  • Validates that required secret files exist before launch.
# ------------------------------------------------------------

# Exit immediately if a command exits with a non-zero status.
# Treat unset variables as an error.
# The return value of a pipeline is the status of the last command to exit with a non-zero status.
set -euo pipefail

echo "[INIT] HVS: Initializing startup sequence..."

# ─────────────────────────── constants ───────────────────────────
readonly SERVICE_ACCOUNT_PATH="./secrets/service-account.json"
readonly RETRY_LIMIT=15
readonly RETRY_DELAY_S=2

# ──────── 1. Ensure secrets directory exists ──────────
# Create the directory for the secrets if it doesn't already exist.
mkdir -p "$(dirname "$SERVICE_ACCOUNT_PATH")"

# ──────── 2. Re-hydrate Google service-account JSON ───────────
# If the service account file doesn't exist, create it from environment variables.
# It checks for a raw JSON string first, then a base64-encoded string.
if [[ ! -f "$SERVICE_ACCOUNT_PATH" ]]; then
  echo "[INFO] Service account file not found. Attempting to create from environment variables..."
  if [[ -n "${GCP_SA_JSON:-}" ]]; then
    echo "[INFO] Found GCP_SA_JSON. Writing to file."
    printf '%s' "$GCP_SA_JSON" > "$SERVICE_ACCOUNT_PATH"
  elif [[ -n "${GCP_SA_B64:-}" ]]; then
    echo "[INFO] Found GCP_SA_B64. Decoding and writing to file."
    # The -d flag decodes the base64 input.
    printf '%s' "$GCP_SA_B64" | base64 -d > "$SERVICE_ACCOUNT_PATH"
  else
    echo "[WARN] Neither GCP_SA_JSON nor GCP_SA_B64 environment variables are set."
  fi

  # If the file was created, set restrictive permissions (read/write for owner only).
  if [[ -f "$SERVICE_ACCOUNT_PATH" ]]; then
    chmod 600 "$SERVICE_ACCOUNT_PATH"
    echo "[INFO] Service account file created successfully: $SERVICE_ACCOUNT_PATH"
  fi
fi

# ────────── 3. Validate that the secret file exists ────────────
tries=0
until [[ -f "$SERVICE_ACCOUNT_PATH" ]]; do
  echo "[WAIT] Waiting for service account file to appear: $SERVICE_ACCOUNT_PATH"
  sleep "$RETRY_DELAY_S"
  (( ++tries >= RETRY_LIMIT )) && {
      echo "[FATAL] Required secret file did not appear after $((RETRY_LIMIT * RETRY_DELAY_S))s. Exiting."
      exit 1
  }
done

# ───────────────────── Diagnostic Information ────────────────────
echo "[INFO] Startup checks complete. Printing diagnostic info..."
echo "[INFO] Current date: $(date)"
echo "[INFO] App path: ${APP_PATH:-/app}"
echo "[INFO] Using camera: ${CAMERA_PATH:-/dev/video0}"
echo "[INFO] Service-account path: $SERVICE_ACCOUNT_PATH"
# BALENA_DEVICE_UUID is often set in BalenaOS environments.
echo "[INFO] Balena device UUID: ${BALENA_DEVICE_UUID:-Not Set}"

# ───────────────────────── Launch the App ────────────────────────
echo "[START] Launching main Python application..."

exec python ./main.py


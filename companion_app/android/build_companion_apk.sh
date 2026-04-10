#!/usr/bin/env bash
# build_companion_apk.sh – Build and sign the Maya companion APK inside Docker.
# Requires: docker (with BuildKit enabled, default since Docker Desktop 20.10+)
#
# Usage:
#   ./build_companion_apk.sh                          # uber-apk-signer (default)
#   ./build_companion_apk.sh --sign-mode keystore \
#       --keystore /path/to/release.jks \
#       --alias    my_key_alias \
#       --store-pass "storePassword" \
#       --key-pass  "keyPassword"
#
# Output (repo-root relative):
#   assets/android/apk/maya-companion-debug.apk
#   assets/android/apk/maya-companion-release-unsigned.apk
#   assets/android/apk/maya-companion-release-signed-uber.apk
#   assets/android/apk/maya-companion-release-signed-keystore.apk  (keystore mode only)

set -euo pipefail

SIGN_MODE="uber"
KEYSTORE_PATH=""
KEY_ALIAS=""
STORE_PASS=""
KEY_PASS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sign-mode)   SIGN_MODE="$2";       shift 2 ;;
    --keystore)    KEYSTORE_PATH="$2";   shift 2 ;;
    --alias)       KEY_ALIAS="$2";       shift 2 ;;
    --store-pass)  STORE_PASS="$2";      shift 2 ;;
    --key-pass)    KEY_PASS="$2";        shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

# ── Preflight ──────────────────────────────────────────────────────────────
if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed or not on PATH." >&2
  echo "       Install Docker Desktop: https://docs.docker.com/get-docker/" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKERFILE="$REPO_ROOT/containers/Dockerfile.apk-builder"
SIGNER_JAR="$REPO_ROOT/assets/signer/uber-apk-signer-1.3.0.jar"
OUTPUT_DIR="$REPO_ROOT/assets/android/apk"

if [[ ! -f "$DOCKERFILE" ]]; then
  echo "ERROR: Missing Dockerfile: $DOCKERFILE" >&2
  exit 1
fi
if [[ ! -f "$SIGNER_JAR" ]]; then
  echo "ERROR: Missing signer asset: $SIGNER_JAR" >&2
  exit 1
fi

BUILD_ARGS=( "--build-arg" "SIGN_MODE=$SIGN_MODE" )

if [[ "$SIGN_MODE" = "keystore" ]]; then
  [[ -n "$KEYSTORE_PATH" ]] || { echo "ERROR: --keystore is required for keystore mode" >&2; exit 1; }
  [[ -n "$KEY_ALIAS"     ]] || { echo "ERROR: --alias is required for keystore mode"    >&2; exit 1; }
  [[ -n "$STORE_PASS"    ]] || { echo "ERROR: --store-pass is required for keystore mode" >&2; exit 1; }
  [[ -f "$KEYSTORE_PATH" ]] || { echo "ERROR: Keystore file not found: $KEYSTORE_PATH"  >&2; exit 1; }

  KEYSTORE_B64=$(base64 -w0 "$KEYSTORE_PATH" 2>/dev/null || base64 "$KEYSTORE_PATH")
  BUILD_ARGS+=(
    "--build-arg" "KEYSTORE_BASE64=$KEYSTORE_B64"
    "--build-arg" "KEY_ALIAS=$KEY_ALIAS"
    "--build-arg" "STORE_PASS=$STORE_PASS"
  )
  [[ -n "$KEY_PASS" ]] && BUILD_ARGS+=( "--build-arg" "KEY_PASS=$KEY_PASS" )
fi

mkdir -p "$OUTPUT_DIR"

echo "[*] Building companion APK inside Docker (sign mode: $SIGN_MODE)..."
DOCKER_BUILDKIT=1 docker build \
  -f "$DOCKERFILE" \
  --target apk-output \
  --output "type=local,dest=$OUTPUT_DIR" \
  "${BUILD_ARGS[@]}" \
  "$REPO_ROOT"

echo ""
echo "[+] Done. APKs written to assets/android/apk/"
ls -lh "$OUTPUT_DIR"/*.apk 2>/dev/null || true

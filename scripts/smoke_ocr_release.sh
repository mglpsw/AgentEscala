#!/usr/bin/env bash
set -euo pipefail

# Smoke test operacional para release 1.5.1 (OCR API + fallback local).
# Uso:
#   BASE_URL=http://localhost:8000 bash scripts/smoke_ocr_release.sh
# Opcional (teste OCR import):
#   ADMIN_TOKEN=... OCR_SAMPLE_FILE=tests/fixtures/escala_exemplo.csv bash scripts/smoke_ocr_release.sh

BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"
OCR_SAMPLE_FILE="${OCR_SAMPLE_FILE:-}"

echo "==> Smoke OCR release 1.5.1 em ${BASE_URL}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERRO: comando obrigatório não encontrado: $1" >&2
    exit 1
  fi
}

require_cmd curl
require_cmd grep

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

curl_json() {
  local path="$1"
  local output_file="$2"
  curl -fsS "${BASE_URL}${path}" -o "$output_file"
}

echo "[1/4] Validando /health"
health_file="${tmp_dir}/health.json"
curl_json "/health" "$health_file"
grep -q '"status"' "$health_file"
grep -q '"version"' "$health_file"
grep -q '"ocr"' "$health_file"
echo "  OK /health"

echo "[2/4] Validando /api/v1/info"
info_file="${tmp_dir}/info.json"
curl_json "/api/v1/info" "$info_file"
grep -q '"ocr"' "$info_file"
grep -q '"api_enabled"' "$info_file"
grep -q '"api_timeout_seconds"' "$info_file"
echo "  OK /api/v1/info"

echo "[3/4] Validando /metrics e métricas OCR"
metrics_file="${tmp_dir}/metrics.txt"
curl_json "/metrics" "$metrics_file"
grep -q 'ocr_requests_total' "$metrics_file"
grep -q 'ocr_api_success_total' "$metrics_file"
grep -q 'ocr_api_failure_total' "$metrics_file"
grep -q 'ocr_fallback_used_total' "$metrics_file"
grep -q 'ocr_api_latency_seconds' "$metrics_file"
echo "  OK /metrics"

echo "[4/4] OCR import (opcional e não destrutivo)"
if [[ -n "$ADMIN_TOKEN" && -n "$OCR_SAMPLE_FILE" ]]; then
  if [[ ! -f "$OCR_SAMPLE_FILE" ]]; then
    echo "  ERRO: OCR_SAMPLE_FILE não encontrado: $OCR_SAMPLE_FILE" >&2
    exit 1
  fi
  upload_file="${tmp_dir}/upload.json"
  http_code="$(
    curl -sS -o "$upload_file" -w "%{http_code}" \
      -H "Authorization: Bearer ${ADMIN_TOKEN}" \
      -F "file=@${OCR_SAMPLE_FILE}" \
      "${BASE_URL}/schedule-imports/"
  )"
  if [[ "$http_code" != "201" ]]; then
    echo "  FALHA: upload OCR retornou HTTP ${http_code}"
    cat "$upload_file"
    exit 1
  fi
  grep -q '"import_id"' "$upload_file"
  echo "  OK import OCR (HTTP 201)"
else
  echo "  SKIP: informe ADMIN_TOKEN e OCR_SAMPLE_FILE para validar import OCR."
fi

cat <<'MANUAL'

Checklist manual curto (fallback local):
  [ ] 1) Validar /api/v1/info com OCR API habilitada e anotar api_base_url.
  [ ] 2) Induzir indisponibilidade controlada da OCR API externa no ambiente de teste.
  [ ] 3) Repetir import OCR e confirmar logs com strategy=fallback_local.
  [ ] 4) Confirmar incremento de ocr_fallback_used_total e ocr_requests_total{strategy="fallback_local"}.
  [ ] 5) Reverter indisponibilidade induzida e validar retorno de strategy=api.

MANUAL

echo "Smoke finalizado com sucesso."

#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$INFRA_DIR")"
ENV_FILE="${ENV_FILE:-$INFRA_DIR/.env.homelab}"
COMPOSE_FILE="$INFRA_DIR/docker-compose.homelab.yml"
ALLOW_DIRTY=false
SKIP_CHECKS=false

usage() {
  cat <<USAGE
Uso: $0 [--allow-dirty] [--skip-checks]

Rebuild canônico do AgentEscala no CT102.

Este script atualiza a stack oficial ativa sem usar o docker-compose.yml da raiz:
  - projeto Compose: agentescala_official
  - compose: infra/docker-compose.homelab.yml
  - env: infra/.env.homelab
  - backend: 192.168.3.155:18000 -> container:8030
  - volume Postgres: agentescala_postgres_data_official18000

Opções:
  --allow-dirty  Permite build com alterações locais não commitadas.
  --skip-checks  Pula npm lint/test antes do build Docker.
  -h, --help     Exibe esta ajuda.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --allow-dirty)
      ALLOW_DIRTY=true
      shift
      ;;
    --skip-checks)
      SKIP_CHECKS=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Erro: argumento desconhecido '$1'" >&2
      usage
      exit 1
      ;;
  esac
done

compose_cmd() {
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  elif command -v docker >/dev/null 2>&1; then
    docker compose "$@"
  else
    echo "Erro: Docker Compose não encontrado (docker compose ou docker-compose)." >&2
    exit 1
  fi
}

require_var() {
  local var_name="$1"
  if [[ -z "${!var_name:-}" ]]; then
    echo "Erro: variável obrigatória '$var_name' não definida em $ENV_FILE" >&2
    exit 1
  fi
}

require_value() {
  local var_name="$1"
  local expected="$2"
  local current="${!var_name:-}"
  if [[ "$current" != "$expected" ]]; then
    echo "Erro: $var_name='$current', esperado '$expected' para o rebuild oficial do CT102." >&2
    exit 1
  fi
}

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Erro: env homelab não encontrado em $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

require_var "COMPOSE_PROJECT_NAME"
require_var "AGENTESCALA_IMAGE"
require_var "BACKEND_BIND_ADDRESS"
require_var "BACKEND_HOST_PORT"
require_var "POSTGRES_VOLUME_NAME"
require_var "INTERNAL_NETWORK_NAME"
require_var "VITE_API_BASE_URL"
require_var "PUBLIC_DOMAIN"
require_var "PUBLIC_PORT"

require_value "COMPOSE_PROJECT_NAME" "agentescala_official"
require_value "AGENTESCALA_IMAGE" "agentescala:homelab"
require_value "BACKEND_BIND_ADDRESS" "192.168.3.155"
require_value "BACKEND_HOST_PORT" "18000"
require_value "POSTGRES_VOLUME_NAME" "agentescala_postgres_data_official18000"
require_value "INTERNAL_NETWORK_NAME" "agentescala_official_internal"
require_value "VITE_API_BASE_URL" "https://escala.ks-sm.net:9443"
require_value "PUBLIC_DOMAIN" "escala.ks-sm.net"
require_value "PUBLIC_PORT" "9443"

cd "$PROJECT_ROOT"

HEAD_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
HEAD_SUBJECT="$(git log -1 --pretty=%s 2>/dev/null || echo unknown)"
echo "=== AgentEscala | Rebuild oficial CT102 ==="
echo "Commit: $HEAD_SHA - $HEAD_SUBJECT"
echo "Compose: $COMPOSE_FILE"
echo "Env: $ENV_FILE"
echo "Projeto: $COMPOSE_PROJECT_NAME"
echo "Backend: $BACKEND_BIND_ADDRESS:$BACKEND_HOST_PORT -> 8030"
echo "Frontend API pública: $VITE_API_BASE_URL"
echo ""

if [[ "$ALLOW_DIRTY" != true ]] && [[ -n "$(git status --porcelain)" ]]; then
  echo "Erro: há alterações locais. Faça commit/stash ou use --allow-dirty conscientemente." >&2
  git status --short >&2
  exit 1
fi

if [[ "$SKIP_CHECKS" != true ]]; then
  echo "Rodando checks do frontend..."
  (cd "$PROJECT_ROOT/frontend" && npm run lint && npm run test)
else
  echo "Checks do frontend pulados por --skip-checks."
fi

echo ""
echo "Validando compose canônico..."
compose_cmd -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" config >/dev/null

echo "Recriando backend oficial com build da imagem $AGENTESCALA_IMAGE..."
DEBUG=false compose_cmd -p "$COMPOSE_PROJECT_NAME" \
  -f "$COMPOSE_FILE" \
  --env-file "$ENV_FILE" \
  up -d --build --force-recreate backend

echo ""
echo "Aguardando health do backend..."
for attempt in {1..30}; do
  if curl -fsS "http://$BACKEND_BIND_ADDRESS:$BACKEND_HOST_PORT/health" >/tmp/agentescala_health.json; then
    echo "Health OK: $(cat /tmp/agentescala_health.json)"
    break
  fi
  if [[ "$attempt" == 30 ]]; then
    echo "Erro: backend não ficou saudável dentro do tempo esperado." >&2
    exit 1
  fi
  sleep 2
done

echo ""
echo "Validando frontend via NPM interno..."
curl -kfsS "https://$PUBLIC_DOMAIN/health" >/tmp/agentescala_npm_health.json
echo "NPM health OK: $(cat /tmp/agentescala_npm_health.json)"

ASSETS="$(curl -kfsS "https://$PUBLIC_DOMAIN/" | grep -o '/assets/[^" ]*\.js' | sort -u)"
if [[ -z "$ASSETS" ]]; then
  echo "Erro: não foi possível localizar bundles JS do frontend." >&2
  exit 1
fi

MATCHED_ASSET=""
while IFS= read -r asset; do
  if curl -kfsS "https://$PUBLIC_DOMAIN$asset" | grep -q "$VITE_API_BASE_URL"; then
    MATCHED_ASSET="$asset"
    break
  fi
done <<< "$ASSETS"

if [[ -z "$MATCHED_ASSET" ]]; then
  echo "Erro: nenhum bundle JS publicado contém $VITE_API_BASE_URL" >&2
  exit 1
fi
echo "Bundle OK: $MATCHED_ASSET contém $VITE_API_BASE_URL"

echo ""
compose_cmd -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
echo ""
echo "Rebuild oficial concluído."

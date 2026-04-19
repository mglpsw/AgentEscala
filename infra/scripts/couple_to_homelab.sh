#!/bin/bash
set -euo pipefail

# Script de acoplamento do AgentEscala ao homelab
# Este script faz o deploy do AgentEscala na sua infraestrutura homelab

echo "=== Deploy do AgentEscala no Homelab ==="
echo ""

# Configuração
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$INFRA_DIR")"
ENV_FILE="${ENV_FILE:-$INFRA_DIR/.env.homelab}"
COMPOSE_FILE="$INFRA_DIR/docker-compose.homelab.yml"
DRY_RUN=false
BUILD_IMAGE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --build)
            BUILD_IMAGE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Erro: argumento desconhecido '$1'"
            echo "Uso: $0 [--build] [--dry-run]"
            exit 1
            ;;
    esac
done

# Verifica se .env.homelab existe
if [ ! -f "$ENV_FILE" ]; then
    echo "Erro: .env.homelab não encontrado!"
    echo "Copie .env.homelab.example para .env.homelab e configure seus valores."
    exit 1
fi

# Carrega variáveis de ambiente
set -a
source "$ENV_FILE"
set +a

PROJECT_NAME="${COMPOSE_PROJECT_NAME:-agentescala}"

compose_cmd() {
    if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
        docker compose "$@"
        return
    fi

    if command -v docker-compose >/dev/null 2>&1; then
        env PYTHONPATH="/usr/lib/python3/dist-packages${PYTHONPATH:+:$PYTHONPATH}" docker-compose "$@"
        return
    fi

    echo "Erro: Docker Compose não encontrado (docker compose ou docker-compose)." >&2
    exit 1
}

require_var() {
    local var_name="$1"
    if [[ -z "${!var_name:-}" ]]; then
        echo "Erro: variável obrigatória '$var_name' não definida em $ENV_FILE"
        exit 1
    fi
}

check_port_free() {
    local port="$1"
    if ss -ltn "( sport = :$port )" | grep -q LISTEN; then
        echo "Erro: a porta $port já está em uso no CT 102. Ajuste BACKEND_HOST_PORT antes do deploy."
        exit 1
    fi
}

rollback_on_error=false

rollback_stack() {
    if [[ "$rollback_on_error" == true ]]; then
        echo ""
        echo "Falha detectada. Revertendo apenas o stack do AgentEscala..."
        compose_cmd -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down || true
    fi
}

trap rollback_stack ERR

require_var "POSTGRES_USER"
require_var "POSTGRES_PASSWORD"
require_var "POSTGRES_DB"
require_var "DATABASE_URL"
require_var "SECRET_KEY"
require_var "ADMIN_EMAIL"
require_var "AGENTESCALA_IMAGE"
require_var "BACKEND_BIND_ADDRESS"
require_var "BACKEND_HOST_PORT"
require_var "POSTGRES_VOLUME_NAME"
require_var "INTERNAL_NETWORK_NAME"
require_var "PUBLIC_DOMAIN"
require_var "PUBLIC_PORT"
require_var "CORS_ALLOW_ORIGINS"

echo "Configuração carregada:"
echo "  - Projeto Compose: $PROJECT_NAME"
echo "  - Domínio público preparado: $PUBLIC_DOMAIN:$PUBLIC_PORT"
echo "  - Bind local do backend: $BACKEND_BIND_ADDRESS:$BACKEND_HOST_PORT"
echo "  - Volume Postgres: $POSTGRES_VOLUME_NAME"
echo "  - Rede interna: $INTERNAL_NETWORK_NAME"
echo "  - Banco de dados: $POSTGRES_DB"
echo ""

check_port_free "$BACKEND_HOST_PORT"

echo "Validando compose do AgentEscala..."
compose_cmd -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" config >/dev/null

# Constrói ou baixa a imagem
echo "Construindo/baixando imagem do AgentEscala..."
if [[ "$BUILD_IMAGE" == true ]]; then
    echo "Construindo imagem local..."
    docker build -t "$AGENTESCALA_IMAGE" "$PROJECT_ROOT"
else
    echo "Baixando imagem do registry..."
    docker pull "$AGENTESCALA_IMAGE" || {
        echo "Aviso: não foi possível baixar a imagem. Construindo localmente..."
        docker build -t "$AGENTESCALA_IMAGE" "$PROJECT_ROOT"
    }
fi

if [[ "$DRY_RUN" == true ]]; then
    echo ""
    echo "Dry-run concluído com sucesso. Nenhuma alteração foi aplicada."
    exit 0
fi

# Faz deploy com docker-compose
echo ""
echo "Fazendo deploy do AgentEscala..."
cd "$INFRA_DIR"
rollback_on_error=true
compose_cmd -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
rollback_on_error=false

echo ""
echo "=== Deploy concluído ==="
echo ""
echo "AgentEscala está em execução!"
echo "  - Endpoint local: http://$BACKEND_BIND_ADDRESS:$BACKEND_HOST_PORT"
echo "  - Health check local: http://$BACKEND_BIND_ADDRESS:$BACKEND_HOST_PORT/health"
echo "  - Publicação prevista via NPM: https://$PUBLIC_DOMAIN:$PUBLIC_PORT"
echo ""
echo "Para ver os logs:"
echo "  docker-compose -p $PROJECT_NAME -f $COMPOSE_FILE logs -f"
echo ""
echo "Para parar:"
echo "  docker-compose -p $PROJECT_NAME -f $COMPOSE_FILE down"
echo ""

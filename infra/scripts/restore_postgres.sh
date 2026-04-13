#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${ENV_FILE:-$INFRA_DIR/.env.homelab}"
COMPOSE_FILE="${COMPOSE_FILE:-$INFRA_DIR/docker-compose.homelab.yml}"
DRY_RUN=false
CONFIRM=false
DUMP_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --confirm-restore)
            CONFIRM=true
            shift
            ;;
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --dump-file)
            DUMP_FILE="$2"
            shift 2
            ;;
        *)
            echo "Uso: $0 --dump-file arquivo.dump [--confirm-restore] [--dry-run] [--env-file arquivo]"
            exit 1
            ;;
    esac
done

if [[ -z "$DUMP_FILE" ]]; then
    echo "Erro: informe --dump-file"
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Erro: env file não encontrado em $ENV_FILE"
    exit 1
fi

if [[ ! -f "$DUMP_FILE" ]]; then
    echo "Erro: dump não encontrado em $DUMP_FILE"
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

PROJECT_NAME="${COMPOSE_PROJECT_NAME:-agentescala}"
DB_CONTAINER_ID="$(docker-compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps -q db)"

if [[ -z "$DB_CONTAINER_ID" ]]; then
    echo "Erro: não foi possível localizar o container do banco do AgentEscala."
    exit 1
fi

echo "=== Restore do PostgreSQL AgentEscala ==="
echo "Projeto Compose: $PROJECT_NAME"
echo "Env file: $ENV_FILE"
echo "Dump: $DUMP_FILE"
echo "Banco alvo: $POSTGRES_DB"
echo "ATENÇÃO: esta operação substitui os dados atuais do AgentEscala."

if [[ "$DRY_RUN" == true ]]; then
    echo "Dry-run: nenhum dado foi restaurado."
    exit 0
fi

if [[ "$CONFIRM" != true ]]; then
    echo "Erro: use --confirm-restore para executar o restore destrutivo do banco do AgentEscala."
    exit 1
fi

docker-compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop backend

cleanup() {
    docker-compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" start backend >/dev/null 2>&1 || true
}

trap cleanup EXIT

docker cp "$DUMP_FILE" "$DB_CONTAINER_ID:/tmp/agentescala_restore.dump"

docker-compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T db sh -c '
    psql -U "$POSTGRES_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '\''$POSTGRES_DB'\'' AND pid <> pg_backend_pid();" &&
    dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB" &&
    createdb -U "$POSTGRES_USER" "$POSTGRES_DB" &&
    pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges /tmp/agentescala_restore.dump &&
    rm -f /tmp/agentescala_restore.dump
'

echo "Restore concluído para o banco $POSTGRES_DB"
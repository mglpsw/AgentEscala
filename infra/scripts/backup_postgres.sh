#!/bin/bash
set -euo pipefail

umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${ENV_FILE:-$INFRA_DIR/.env.homelab}"
COMPOSE_FILE="${COMPOSE_FILE:-$INFRA_DIR/docker-compose.homelab.yml}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DRY_RUN=false
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        *)
            echo "Uso: $0 [--dry-run] [--env-file arquivo] [--output-dir diretorio]"
            exit 1
            ;;
    esac
done

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Erro: env file não encontrado em $ENV_FILE"
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

PROJECT_NAME="${COMPOSE_PROJECT_NAME:-agentescala}"
BACKUP_ROOT="${OUTPUT_DIR:-${BACKUP_DIR:-$INFRA_DIR/backups}}"
TARGET_DIR="$BACKUP_ROOT/$TIMESTAMP"
ARCHIVE_FILE="$TARGET_DIR/${POSTGRES_DB}.dump"
METADATA_FILE="$TARGET_DIR/metadata.env"

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

mkdir -p "$TARGET_DIR"

echo "=== Backup do PostgreSQL AgentEscala ==="
echo "Projeto Compose: $PROJECT_NAME"
echo "Env file: $ENV_FILE"
echo "Destino: $ARCHIVE_FILE"

if [[ "$DRY_RUN" == true ]]; then
    echo "Dry-run: nenhum dump foi gerado."
    exit 0
fi

compose_cmd -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps db >/dev/null

compose_cmd -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T db \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$ARCHIVE_FILE"

if [[ ! -s "$ARCHIVE_FILE" ]]; then
    echo "Erro: backup gerado vazio em $ARCHIVE_FILE"
    exit 1
fi

cat > "$METADATA_FILE" <<EOF
TIMESTAMP=$TIMESTAMP
POSTGRES_DB=$POSTGRES_DB
POSTGRES_USER=$POSTGRES_USER
COMPOSE_PROJECT_NAME=$PROJECT_NAME
BACKEND_BIND_ADDRESS=${BACKEND_BIND_ADDRESS:-127.0.0.1}
BACKEND_HOST_PORT=${BACKEND_HOST_PORT:-18000}
DUMP_FILE=$(basename "$ARCHIVE_FILE")
EOF

echo "Backup concluído: $ARCHIVE_FILE"
echo "Metadados: $METADATA_FILE"

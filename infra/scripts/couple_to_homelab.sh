#!/bin/bash
set -e

# Script de acoplamento do AgentEscala ao homelab
# Este script faz o deploy do AgentEscala na sua infraestrutura homelab

echo "=== Deploy do AgentEscala no Homelab ==="
echo ""

# Configuração
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$INFRA_DIR")"
ENV_FILE="$INFRA_DIR/.env.homelab"
COMPOSE_FILE="$INFRA_DIR/docker-compose.homelab.yml"
EXTERNAL_PORT="9443"

# Verifica se .env.homelab existe
if [ ! -f "$ENV_FILE" ]; then
    echo "Erro: .env.homelab não encontrado!"
    echo "Copie .env.homelab.example para .env.homelab e configure seus valores."
    exit 1
fi

# Carrega variáveis de ambiente
source "$ENV_FILE"

echo "Configuração carregada:"
echo "  - Domínio: $DOMAIN (porta externa $EXTERNAL_PORT)"
echo "  - Rede do Traefik: $TRAEFIK_NETWORK"
echo "  - Banco de dados: $POSTGRES_DB"
echo ""

# Verifica se a rede do Traefik existe
if ! docker network inspect "$TRAEFIK_NETWORK" >/dev/null 2>&1; then
    echo "Erro: a rede Traefik '$TRAEFIK_NETWORK' não existe!"
    echo "Crie-a antes ou revise sua configuração de homelab."
    exit 1
fi

# Constrói ou baixa a imagem
echo "Construindo/baixando imagem do AgentEscala..."
if [ "$1" == "--build" ]; then
    echo "Construindo imagem local..."
    docker build -t ghcr.io/mglpsw/agentescala:latest "$PROJECT_ROOT"
else
    echo "Baixando imagem do registry..."
    docker pull ghcr.io/mglpsw/agentescala:latest || {
        echo "Aviso: não foi possível baixar a imagem. Construindo localmente..."
        docker build -t ghcr.io/mglpsw/agentescala:latest "$PROJECT_ROOT"
    }
fi

# Faz deploy com docker-compose
echo ""
echo "Fazendo deploy do AgentEscala..."
cd "$INFRA_DIR"
docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

echo ""
echo "=== Deploy concluído ==="
echo ""
echo "AgentEscala está em execução!"
echo "  - URL: https://$DOMAIN:$EXTERNAL_PORT"
echo "  - Health check: https://$DOMAIN:$EXTERNAL_PORT/health"
echo ""
echo "Para ver os logs:"
echo "  docker-compose -f $COMPOSE_FILE logs -f"
echo ""
echo "Para parar:"
echo "  docker-compose -f $COMPOSE_FILE down"
echo ""

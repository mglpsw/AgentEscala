#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${ENV_FILE:-$INFRA_DIR/.env.homelab}"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Erro: env file não encontrado em $ENV_FILE"
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

echo "=== Plano de Publicação NPM do AgentEscala ==="
echo "Host público: ${PUBLIC_DOMAIN}:${PUBLIC_PORT}"
echo "Upstream esperado: http://${BACKEND_BIND_ADDRESS}:${BACKEND_HOST_PORT}"
echo "CORS_ALLOW_ORIGINS: ${CORS_ALLOW_ORIGINS}"
echo ""
echo "Passos seguros no Nginx Proxy Manager:"
echo "1. Usar um único Proxy Host habilitado para ${PUBLIC_DOMAIN}."
echo "2. Forward Hostname/IP: ${BACKEND_BIND_ADDRESS}."
echo "3. Forward Port: ${BACKEND_HOST_PORT}."
echo "4. Scheme: http."
echo "5. Dentro do CT 102 o NPM escuta em 443; o :${PUBLIC_PORT} é port-forward externo do roteador."
echo "6. Se houver duplicata para ${PUBLIC_DOMAIN}, manter apenas uma habilitada."
echo "7. Testar /health, /api/v1/info, /login e login real após salvar."
echo ""
if [[ "${BACKEND_BIND_ADDRESS}" == "127.0.0.1" ]]; then
    echo "Aviso: se o NPM estiver em container separado, 127.0.0.1 não será acessível como upstream."
    echo "Nesse caso, ajuste BACKEND_BIND_ADDRESS para o IP LAN do CT 102 e reexecute este plano."
fi

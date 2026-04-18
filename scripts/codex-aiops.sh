#!/usr/bin/env bash
# Codex CLI apontado para o AIOps Agent Router via proxy local.
# Inicia o proxy automaticamente se não estiver rodando.
#
# Uso (idêntico ao codex):
#   ./scripts/codex-aiops.sh                    # sessão interativa
#   ./scripts/codex-aiops.sh "refatore X"       # prompt inicial
#   ./scripts/codex-aiops.sh exec "liste scripts/" # exec não-interativo
#   ./scripts/codex-aiops.sh -m chat:raciocinio "analise a arquitetura"
#
# Variáveis:
#   AGENT_MODEL=chat:raciocinio   modelo a usar
#   AGENT_URL=http://...          upstream diferente do padrão
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROXY_SCRIPT="$REPO_ROOT/scripts/codex-proxy.py"
PROXY_PORT=8099
PROXY_LOG="/tmp/codex-aiops-proxy.log"
AGENT_URL="${AGENT_URL:-http://192.168.3.155:8010}"
AGENT_MODEL="${AGENT_MODEL:-chat:codigo}"
export AIOPS_API_KEY=dummy

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

# ── Garantir que o proxy está rodando ────────────────────────────────────────
proxy_running() {
  curl -sf --max-time 2 "http://localhost:${PROXY_PORT}/health" &>/dev/null
}

start_proxy() {
  echo -e "${CYAN}▸${NC} Iniciando proxy Responses API → Chat Completions..."
  nohup python3 "$PROXY_SCRIPT" \
    --port "$PROXY_PORT" \
    --upstream "$AGENT_URL" \
    >"$PROXY_LOG" 2>&1 &
  echo $! > /tmp/codex-aiops-proxy.pid
  # Aguardar proxy subir (máx 8s)
  for i in $(seq 1 8); do
    sleep 1
    if proxy_running; then
      echo -e "${GREEN}✓${NC} Proxy ativo em http://localhost:${PROXY_PORT} (upstream: ${AGENT_URL})"
      return 0
    fi
  done
  echo -e "${YELLOW}⚠${NC} Proxy demorou para subir. Verifique: $PROXY_LOG"
  return 1
}

if ! proxy_running; then
  start_proxy
else
  echo -e "${GREEN}✓${NC} Proxy já ativo em http://localhost:${PROXY_PORT}"
fi

# ── Lançar codex com provider aiops ─────────────────────────────────────────
cd "$REPO_ROOT"
exec codex \
  -c "model=${AGENT_MODEL}" \
  -c "model_provider=aiops" \
  "$@"

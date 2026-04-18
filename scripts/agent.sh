#!/usr/bin/env bash
# Agent terminal do AgentEscala.
# Usa o agent-router (OpenAI-compatible) como backend LLM.
# Integrado com git: lê contexto do repo, commita mudanças automaticamente.
#
# Uso:
#   ./scripts/agent.sh                        # sessão interativa (aider)
#   ./scripts/agent.sh "refatore o shift_service"  # prompt inicial + interativo
#   ./scripts/agent.sh --query "o que faz /health?"    # consulta rápida (sem editar)
#   ./scripts/agent.sh --model chat:raciocinio         # modelo específico
#   ./scripts/agent.sh --external                      # forçar URL externa
#   ./scripts/agent.sh --list-models                   # listar modelos disponíveis
#   ./scripts/agent.sh --git                           # resumo git + contexto
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ─── Cores ───────────────────────────────────────────────────────────────────
BOLD='\033[1m'; CYAN='\033[0;36m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${CYAN}▸${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
err()   { echo -e "${RED}✗${NC} $*" >&2; }

# ─── Config padrão ───────────────────────────────────────────────────────────
AGENT_LOCAL_URL="http://192.168.3.155:8010"
AGENT_EXTERNAL_URL="https://api.ks-sm.net:9443"
AGENT_MODEL="${AGENT_MODEL:-chat:codigo}"
MODE="interactive"
PROMPT=""
FORCE_EXTERNAL=false

# ─── Modelos disponíveis ─────────────────────────────────────────────────────
MODELS_LOCAL=(
  "chat:codigo          → código, edição de arquivos (padrão)"
  "chat:rapido          → respostas rápidas e simples"
  "chat:raciocinio      → raciocínio profundo e arquitetura"
  "chat:pro             → tarefas complexas gerais"
  "chat:auto            → router automático local"
)
MODELS_ROUTER=(
  "agent-router:aiops         → AIOps: decisão inteligente de roteamento"
  "agent-router:auto          → automático (deixa o router escolher)"
  "agent-router:code-local    → código com modelo local"
  "agent-router:reasoning-local → raciocínio local"
  "agent-router:deep-local    → análise profunda local"
  "agent-router:gpt-external  → GPT/OpenAI via router"
  "agent-router:codex-external → Codex OpenAI via router"
)

# ─── Parse de argumentos ─────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --query|-q)       MODE="query";    PROMPT="${2:-}"; shift 2 ;;
    --model|-m)       AGENT_MODEL="$2"; shift 2 ;;
    --external|-e)    FORCE_EXTERNAL=true; shift ;;
    --list-models|-l) MODE="list-models"; shift ;;
    --git|-g)         MODE="git"; shift ;;
    --help|-h)        MODE="help"; shift ;;
    --)               shift; PROMPT="$*"; break ;;
    *)                PROMPT="$1"; shift ;;
  esac
done

# ─── Help ────────────────────────────────────────────────────────────────────
show_help() {
  echo -e "${BOLD}agent.sh${NC} — Terminal agent do AgentEscala"
  echo ""
  echo "  Uso: ./scripts/agent.sh [opção] [prompt]"
  echo ""
  echo "  Modos:"
  echo "    (sem args)                sessão interativa — edita arquivos com git"
  echo "    \"prompt aqui\"            sessão interativa com prompt inicial"
  echo "    --query / -q \"pergunta\"   consulta rápida sem editar arquivos"
  echo "    --git / -g                resumo git e contexto do repo"
  echo "    --list-models / -l        listar modelos disponíveis"
  echo ""
  echo "  Opções:"
  echo "    --model / -m MODELO       modelo a usar (padrão: chat:codigo)"
  echo "    --external / -e           forçar URL externa (api.ks-sm.net)"
  echo "    --help / -h               esta ajuda"
  echo ""
  echo "  Variáveis de ambiente:"
  echo "    AGENT_MODEL=chat:raciocinio   sobrescrever modelo"
  echo "    AGENT_URL=http://...          sobrescrever URL do agent-router"
  echo ""
  echo "  Exemplos:"
  echo "    ./scripts/agent.sh                             # sessão interativa"
  echo "    ./scripts/agent.sh \"adiciona rota GET /api/teams\""
  echo "    ./scripts/agent.sh -q \"como funciona o shift_service?\""
  echo "    ./scripts/agent.sh -m agent-router:aiops       # usar AIOps"
  echo "    ./scripts/agent.sh -m agent-router:gpt-external # usar OpenAI"
  echo "    ./scripts/agent.sh -l                          # ver modelos"
}

# ─── Listar modelos ──────────────────────────────────────────────────────────
list_models() {
  echo ""
  echo -e "${BOLD}  Modelos locais (via agent-router):${NC}"
  for m in "${MODELS_LOCAL[@]}"; do echo "    $m"; done
  echo ""
  echo -e "${BOLD}  Modelos do router (AIOps + externos):${NC}"
  for m in "${MODELS_ROUTER[@]}"; do echo "    $m"; done
  echo ""
  echo -e "  ${CYAN}Modelo atual:${NC} ${BOLD}${AGENT_MODEL}${NC}"
  echo ""
}

# ─── Detectar URL do agent-router ────────────────────────────────────────────
detect_api_url() {
  if [[ -n "${AGENT_URL:-}" ]]; then
    echo "$AGENT_URL"
    return
  fi
  if [[ "$FORCE_EXTERNAL" == true ]]; then
    echo "$AGENT_EXTERNAL_URL"
    return
  fi
  # Testar local primeiro (timeout 2s)
  if curl -sf --max-time 2 "${AGENT_LOCAL_URL}/health" &>/dev/null; then
    echo "$AGENT_LOCAL_URL"
  else
    warn "agent-router local não acessível, usando URL externa..."
    echo "$AGENT_EXTERNAL_URL"
  fi
}

# ─── Resumo git ──────────────────────────────────────────────────────────────
show_git_context() {
  echo ""
  echo -e "${BOLD}  Contexto Git — AgentEscala${NC}"
  echo ""
  echo -e "  Branch: ${CYAN}$(git rev-parse --abbrev-ref HEAD)${NC}"
  STAGED=$(git diff --cached --name-only | wc -l | tr -d ' ')
  UNSTAGED=$(git diff --name-only | wc -l | tr -d ' ')
  UNTRACKED=$(git ls-files --others --exclude-standard | wc -l | tr -d ' ')
  echo "  Staged: ${STAGED}  |  Modificados: ${UNSTAGED}  |  Não rastreados: ${UNTRACKED}"
  echo ""
  echo -e "  ${BOLD}Últimos commits:${NC}"
  git log --oneline -5 | sed 's/^/    /'
  if [[ "$STAGED" -gt 0 || "$UNSTAGED" -gt 0 ]]; then
    echo ""
    echo -e "  ${BOLD}Diff resumido:${NC}"
    git diff --stat | sed 's/^/    /'
  fi
  echo ""
}

# ─── Consulta rápida (sem editar arquivos) ───────────────────────────────────
run_query() {
  local url="$1"
  local model="$2"
  local prompt="$3"

  if [[ -z "$prompt" ]]; then
    err "Informe o prompt para --query"
    echo "  Uso: ./scripts/agent.sh --query \"sua pergunta aqui\""
    exit 1
  fi

  # Contexto git como system prompt
  local branch
  branch="$(git rev-parse --abbrev-ref HEAD)"
  local last_commits
  last_commits="$(git log --oneline -3)"
  local git_status
  git_status="$(git status --short | head -10)"

  local system_prompt="Você é um assistente especializado no projeto AgentEscala (FastAPI + React + PostgreSQL, homelab CT102). Branch atual: ${branch}. Últimos commits: ${last_commits}. Status: ${git_status}. Responda em português do Brasil, de forma concisa e prática."

  local payload
  payload=$(printf '{"model":"%s","messages":[{"role":"system","content":"%s"},{"role":"user","content":"%s"}],"max_tokens":2048}' \
    "$model" \
    "$(echo "$system_prompt" | sed 's/"/\\"/g' | tr '\n' ' ')" \
    "$(echo "$prompt" | sed 's/"/\\"/g')")

  info "Consultando ${model} em ${url}..."
  echo ""

  local response
  response=$(curl -sf "${url}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer dummy" \
    -d "$payload" 2>&1)

  if echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])" 2>/dev/null; then
    :
  else
    err "Falha na resposta do agent-router:"
    echo "$response" | head -5
    exit 1
  fi
  echo ""
}

# ─── Sessão interativa (aider) ───────────────────────────────────────────────
run_interactive() {
  local url="$1"
  local model="$2"

  export OPENAI_API_KEY=dummy
  export OPENAI_API_BASE="${url}/v1"

  echo ""
  echo -e "${BOLD}  AgentEscala — Sessão Interativa${NC}"
  echo -e "  Modelo:  ${CYAN}${model}${NC}"
  echo -e "  Backend: ${CYAN}${url}${NC}"
  echo -e "  Git:     $(git rev-parse --abbrev-ref HEAD)"
  echo ""
  echo -e "  ${YELLOW}Comandos úteis dentro do aider:${NC}"
  echo "    /add <arquivo>    → adicionar arquivo ao contexto"
  echo "    /git status       → ver estado git"
  echo "    /run <comando>    → executar comando shell"
  echo "    /commit           → commitar mudanças feitas pelo agente"
  echo "    /diff             → ver diff atual"
  echo "    /quit             → sair"
  echo ""

  local aider_args=(
    --model "openai/${model}"
    --no-stream
    --auto-commits
    --read CLAUDE.md
    --read AGENTS.md
    --show-model-warnings=false
  )

  if [[ -n "$PROMPT" ]]; then
    aider_args+=(--message "$PROMPT")
  fi

  exec aider "${aider_args[@]}"
}

# ─── Main ────────────────────────────────────────────────────────────────────
case "$MODE" in
  help)
    show_help
    ;;
  list-models)
    list_models
    ;;
  git)
    show_git_context
    ;;
  query)
    API_URL="$(detect_api_url)"
    run_query "$API_URL" "$AGENT_MODEL" "$PROMPT"
    ;;
  interactive)
    API_URL="$(detect_api_url)"
    ok "agent-router: ${API_URL}"
    run_interactive "$API_URL" "$AGENT_MODEL"
    ;;
esac

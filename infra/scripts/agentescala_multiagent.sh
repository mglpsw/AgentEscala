#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$INFRA_DIR")"
PROMPT_FILE="$PROJECT_ROOT/docs/agents/agentescala_multiagent_homelab.prompt.md"
OUTPUT_DIR="$PROJECT_ROOT/reports"
MODE="review"
MODEL="${CODEX_MODEL:-gpt-5.4}"
EFFORT="${CODEX_EFFORT:-high}"
SANDBOX="read-only"
EXTRA_PROMPT=""
OUTPUT_FILE=""

usage() {
  cat <<USAGE
Uso: $0 [modo] [opcoes] [-- prompt extra]

Comando multiagente local do AgentEscala. Ele chama o Codex CLI com um contrato
multiagente versionado em docs/agents/agentescala_multiagent_homelab.prompt.md.

Modos:
  review          Auditoria sem alterar arquivos (default).
  fix            Permite corrigir arquivos do repo, sem deploy Docker.
  rebuild-plan   Planeja/revisa rebuild oficial, sem executar Docker.
  rebuild-run    Executa a rotina de rebuild oficial do CT102. Exige --danger.

Opcoes:
  --model NOME       Modelo Codex/OpenAI (default: CODEX_MODEL ou gpt-5.4).
  --effort NIVEL     Esforco de raciocinio (default: CODEX_EFFORT ou high).
  --danger           Usa sandbox danger-full-access. Necessario para rebuild-run.
  --output ARQUIVO   Caminho para salvar a ultima resposta do agente.
  -h, --help         Exibe esta ajuda.

Exemplos:
  $0 review -- "revise as mudancas pendentes e aponte riscos"
  $0 fix -- "corrija a migration recorrente e rode testes"
  $0 rebuild-plan
  $0 rebuild-run --danger -- "rode a build canonica e valide /calendar"

Pre-requisito de API local:
  export OPENAI_API_KEY='...'
  printenv OPENAI_API_KEY | codex login --with-api-key
USAGE
}

if [[ $# -gt 0 && "$1" != --* ]]; then
  MODE="$1"
  shift
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODEL="$2"
      shift 2
      ;;
    --effort)
      EFFORT="$2"
      shift 2
      ;;
    --danger)
      SANDBOX="danger-full-access"
      shift
      ;;
    --output)
      OUTPUT_FILE="$2"
      shift 2
      ;;
    --)
      shift
      EXTRA_PROMPT="$*"
      break
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

case "$MODE" in
  review)
    SANDBOX="read-only"
    MODE_PROMPT="Modo review: inspecione, rode comandos somente de leitura e entregue diagnostico. Nao edite arquivos."
    ;;
  fix)
    [[ "$SANDBOX" == "read-only" ]] && SANDBOX="workspace-write"
    MODE_PROMPT="Modo fix: voce pode editar arquivos do repositorio e rodar lint/test/build. Nao execute deploy Docker nem reinicie servicos."
    ;;
  rebuild-plan)
    SANDBOX="read-only"
    MODE_PROMPT="Modo rebuild-plan: gere plano e checklist para rebuild oficial, sem executar Docker nem alterar arquivos."
    ;;
  rebuild-run)
    if [[ "$SANDBOX" != "danger-full-access" ]]; then
      echo "Erro: rebuild-run precisa de --danger porque Docker/Compose ficam fora do sandbox do workspace." >&2
      exit 1
    fi
    MODE_PROMPT="Modo rebuild-run: execute o rebuild oficial com ./infra/scripts/rebuild_official_homelab.sh, valide health/auth/calendar e reporte evidencias. Nao toque em stacks nao relacionadas."
    ;;
  *)
    echo "Erro: modo invalido '$MODE'." >&2
    usage
    exit 1
    ;;
esac

if ! command -v codex >/dev/null 2>&1; then
  echo "Erro: Codex CLI nao encontrado no PATH." >&2
  exit 1
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "Erro: prompt multiagente nao encontrado em $PROMPT_FILE" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
if [[ -z "$OUTPUT_FILE" ]]; then
  TS="$(date -u +%Y%m%dT%H%M%SZ)"
  OUTPUT_FILE="$OUTPUT_DIR/agentescala_multiagent_${MODE}_${TS}.md"
fi

{
  cat "$PROMPT_FILE"
  printf "\n## Modo solicitado\n\n%s\n" "$MODE_PROMPT"
  if [[ -n "$EXTRA_PROMPT" ]]; then
    printf "\n## Pedido adicional do usuario\n\n%s\n" "$EXTRA_PROMPT"
  fi
} | codex exec \
  --cd "$PROJECT_ROOT" \
  --model "$MODEL" \
  --config "model_reasoning_effort=\"$EFFORT\"" \
  --sandbox "$SANDBOX" \
  --output-last-message "$OUTPUT_FILE" \
  -

echo ""
echo "Resposta final salva em: $OUTPUT_FILE"

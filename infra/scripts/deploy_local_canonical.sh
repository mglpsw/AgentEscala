#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REBUILD_SCRIPT="$SCRIPT_DIR/rebuild_official_homelab.sh"
VALIDATION_SCRIPT="$SCRIPT_DIR/run_homelab_validation.sh"
TARGET_BRANCH="${TARGET_BRANCH:-main}"
REMOTE_NAME="${REMOTE_NAME:-origin}"
SKIP_GIT_SYNC=false
REBUILD_ARGS=()

usage() {
  cat <<USAGE
Uso: $0 [opções] [-- <args-do-rebuild>]

Executa o deploy canônico local do AgentEscala no CT102.
Sequência padrão:
  1) valida git limpo e branch atual;
  2) sincroniza com origin/main (fast-forward only);
  3) executa infra/scripts/rebuild_official_homelab.sh;
  4) roda validação pós-deploy.

Opções:
  --skip-git-sync       Pula fetch/merge e mantém o commit local atual.
  --target-branch NAME  Branch canônica para sincronizar (default: main).
  --remote NAME         Remote para sincronização (default: origin).
  -h, --help            Exibe esta ajuda.

Argumentos após -- são repassados para o rebuild_oficial_homelab.sh.
Exemplos:
  $0
  $0 -- --allow-dirty
  $0 --skip-git-sync -- --skip-checks
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-git-sync)
      SKIP_GIT_SYNC=true
      shift
      ;;
    --target-branch)
      TARGET_BRANCH="$2"
      shift 2
      ;;
    --remote)
      REMOTE_NAME="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      REBUILD_ARGS=("$@")
      break
      ;;
    *)
      echo "Erro: argumento desconhecido '$1'" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ! -x "$REBUILD_SCRIPT" ]]; then
  echo "Erro: script de rebuild não encontrado/executável: $REBUILD_SCRIPT" >&2
  exit 1
fi

if [[ ! -x "$VALIDATION_SCRIPT" ]]; then
  echo "Erro: script de validação não encontrado/executável: $VALIDATION_SCRIPT" >&2
  exit 1
fi

cd "$PROJECT_ROOT"

echo "=== AgentEscala | Deploy canônico local ==="
echo "Repo: $PROJECT_ROOT"
echo "Branch atual: $(git branch --show-current)"
echo "Commit atual: $(git rev-parse --short HEAD)"

git diff --stat

if [[ "$SKIP_GIT_SYNC" != true ]]; then
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "Erro: repositório com alterações locais. Commit/stash antes do deploy ou use --skip-git-sync." >&2
    git status --short >&2
    exit 1
  fi

  CURRENT_BRANCH="$(git branch --show-current)"
  if [[ "$CURRENT_BRANCH" != "$TARGET_BRANCH" ]]; then
    echo "Erro: branch atual '$CURRENT_BRANCH'. Faça checkout em '$TARGET_BRANCH' para deploy canônico." >&2
    exit 1
  fi

  echo "Sincronizando com $REMOTE_NAME/$TARGET_BRANCH (fast-forward only)..."
  git fetch "$REMOTE_NAME" "$TARGET_BRANCH"
  git merge --ff-only "${REMOTE_NAME}/${TARGET_BRANCH}"
else
  echo "Aviso: sincronização git pulada por --skip-git-sync."
fi

echo ""
echo "[1/2] Rebuild oficial da stack..."
"$REBUILD_SCRIPT" "${REBUILD_ARGS[@]}"

echo ""
echo "[2/2] Validação pós-deploy..."
"$VALIDATION_SCRIPT"

echo ""
echo "Deploy canônico local concluído com sucesso."

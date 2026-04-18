#!/usr/bin/env bash
# Cria uma nova branch de trabalho a partir da main atualizada.
# Uso: ./scripts/git-start-feature.sh feat/nome-da-tarefa
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${CYAN}[info]${NC} $*"; }
warn()    { echo -e "${YELLOW}[warn]${NC} $*"; }
success() { echo -e "${GREEN}[ok]${NC} $*"; }
error()   { echo -e "${RED}[erro]${NC} $*" >&2; }

BRANCH_NAME="${1:-}"

if [[ -z "$BRANCH_NAME" ]]; then
    error "Informe o nome da branch."
    echo ""
    echo "  Uso: $0 <nome-da-branch>"
    echo ""
    echo "  Exemplos:"
    echo "    $0 feat/ocr-pdf-parsing"
    echo "    $0 fix/swap-validation"
    echo "    $0 refactor/shift-service"
    echo "    $0 docs/api-endpoints"
    echo "    $0 chore/update-deps"
    echo ""
    echo "  Prefixos válidos: feat/ fix/ refactor/ docs/ chore/ test/"
    exit 1
fi

# Validar formato do nome da branch
if ! echo "$BRANCH_NAME" | grep -qE '^(feat|fix|refactor|docs|chore|test)/.+'; then
    warn "Nome de branch não segue a convenção: feat/ fix/ refactor/ docs/ chore/ test/"
    warn "Branch será criada mesmo assim, mas considere renomear."
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

# Verificar alterações locais
if ! git diff --quiet || ! git diff --cached --quiet; then
    error "Há alterações locais não commitadas. Commite ou faça stash antes de criar uma nova branch."
    git status --short
    exit 1
fi

# Verificar se a branch já existe
if git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}"; then
    warn "Branch '${BRANCH_NAME}' já existe localmente."
    echo ""
    echo "  Para ir para ela: git checkout ${BRANCH_NAME}"
    exit 1
fi

# Atualizar main antes de criar a branch
info "Atualizando main antes de criar a branch..."
git fetch origin

if [[ "$CURRENT_BRANCH" != "main" ]]; then
    info "Mudando para main..."
    git checkout main
fi

LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse origin/main)"

if [[ "$LOCAL" != "$REMOTE" ]]; then
    BEHIND="$(git rev-list HEAD..origin/main --count)"
    info "Aplicando ${BEHIND} commit(s) novos da origin/main..."
    git merge --ff-only origin/main
fi

# Criar a branch
info "Criando branch '${BRANCH_NAME}' a partir de main..."
git checkout -b "$BRANCH_NAME"

success "Branch '${BRANCH_NAME}' criada e ativa."
echo ""
echo "  Próximos passos:"
echo "    Edite os arquivos necessários"
echo "    git add <arquivo>"
echo "    git commit -m \"feat: descrição\""
echo "    git push origin ${BRANCH_NAME}"
echo "    gh pr create --title \"feat: ...\" --body \"...\""

#!/usr/bin/env bash
# Atualiza o repositório AgentEscala da main de forma segura.
# Para antes de sobrescrever se houver alterações locais não commitadas.
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

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

info "Branch atual: ${CURRENT_BRANCH}"

# Verificar alterações locais não commitadas
if ! git diff --quiet || ! git diff --cached --quiet; then
    error "Há alterações locais não commitadas. Não vou atualizar para evitar perda de trabalho."
    echo ""
    echo "  Opções:"
    echo "    git stash push -m 'wip: descrição'   → salvar temporariamente"
    echo "    git add <arquivo> && git commit -m '...' → commitar antes"
    echo ""
    git status --short
    exit 1
fi

# Buscar atualizações do remoto (sem alterar arquivos locais)
info "Buscando atualizações de origin..."
git fetch origin

if [[ "$CURRENT_BRANCH" == "main" ]]; then
    LOCAL="$(git rev-parse HEAD)"
    REMOTE="$(git rev-parse origin/main)"

    if [[ "$LOCAL" == "$REMOTE" ]]; then
        success "main já está atualizada. Nada a fazer."
        exit 0
    fi

    BEHIND="$(git rev-list HEAD..origin/main --count)"
    AHEAD="$(git rev-list origin/main..HEAD --count)"

    if [[ "$AHEAD" -gt 0 ]]; then
        warn "Sua main local está ${AHEAD} commit(s) à frente de origin/main."
        warn "Isso não é esperado. Verifique antes de continuar:"
        echo "    git log --oneline origin/main..HEAD"
        exit 1
    fi

    info "Aplicando ${BEHIND} commit(s) novos da origin/main (--ff-only)..."
    # --ff-only garante que só avança se não houver divergência
    if git merge --ff-only origin/main; then
        success "main atualizada com sucesso."
        git log --oneline -3
    else
        error "Merge fast-forward falhou. Sua main divergiu de origin/main."
        echo "  Verifique com: git log --oneline --graph HEAD origin/main"
        exit 1
    fi

else
    BEHIND_MAIN="$(git rev-list HEAD..origin/main --count)"
    AHEAD_MAIN="$(git rev-list origin/main..HEAD --count)"

    info "Você está na branch '${CURRENT_BRANCH}'."
    info "  ${AHEAD_MAIN} commit(s) à frente de origin/main"
    info "  ${BEHIND_MAIN} commit(s) atrás de origin/main"

    if [[ "$BEHIND_MAIN" -eq 0 ]]; then
        success "Sua branch está atualizada com origin/main."
    else
        warn "Sua branch está ${BEHIND_MAIN} commit(s) atrás de origin/main."
        echo ""
        echo "  Para atualizar sua branch com as últimas mudanças da main:"
        echo "    git merge origin/main          (conservador, cria merge commit)"
        echo "    git rebase origin/main         (histórico linear, mais invasivo)"
        echo ""
        echo "  Recomendação: use merge se não tiver certeza do impacto do rebase."
    fi
fi

#!/usr/bin/env bash
# Exibe um resumo completo do estado git do repositório AgentEscala.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BOLD='\033[1m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m'

sep() { echo -e "${GRAY}─────────────────────────────────────────${NC}"; }

echo ""
sep
echo -e "${BOLD}  AgentEscala — Estado Git${NC}"
sep

# Branch e estado remoto
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo -e "  Branch:    ${CYAN}${CURRENT_BRANCH}${NC}"

# Verificar se há remote configurado
if git remote get-url origin &>/dev/null; then
    REMOTE_URL="$(git remote get-url origin)"
    echo -e "  Remote:    ${GRAY}${REMOTE_URL}${NC}"

    # Buscar silenciosamente para comparar (sem alterar arquivos)
    git fetch origin --quiet 2>/dev/null || true

    if git rev-parse "origin/${CURRENT_BRANCH}" &>/dev/null; then
        AHEAD="$(git rev-list "origin/${CURRENT_BRANCH}..HEAD" --count 2>/dev/null || echo 0)"
        BEHIND="$(git rev-list "HEAD..origin/${CURRENT_BRANCH}" --count 2>/dev/null || echo 0)"

        if [[ "$AHEAD" -eq 0 && "$BEHIND" -eq 0 ]]; then
            echo -e "  Remoto:    ${GREEN}sincronizado com origin/${CURRENT_BRANCH}${NC}"
        else
            [[ "$AHEAD" -gt 0 ]] && echo -e "  Remoto:    ${YELLOW}${AHEAD} commit(s) à frente de origin/${CURRENT_BRANCH}${NC}"
            [[ "$BEHIND" -gt 0 ]] && echo -e "  Remoto:    ${RED}${BEHIND} commit(s) atrás de origin/${CURRENT_BRANCH}${NC}"
        fi
    else
        echo -e "  Remoto:    ${YELLOW}branch não existe no origin ainda${NC}"
    fi

    # Divergência em relação à main
    if [[ "$CURRENT_BRANCH" != "main" ]] && git rev-parse "origin/main" &>/dev/null; then
        AHEAD_MAIN="$(git rev-list "origin/main..HEAD" --count 2>/dev/null || echo 0)"
        BEHIND_MAIN="$(git rev-list "HEAD..origin/main" --count 2>/dev/null || echo 0)"
        echo -e "  vs main:   ${CYAN}+${AHEAD_MAIN} / -${BEHIND_MAIN}${NC} (à frente / atrás)"
    fi
else
    echo -e "  Remote:    ${YELLOW}nenhum remoto configurado${NC}"
fi

sep

# Alterações locais
STAGED="$(git diff --cached --name-only | wc -l | tr -d ' ')"
UNSTAGED="$(git diff --name-only | wc -l | tr -d ' ')"
UNTRACKED="$(git ls-files --others --exclude-standard | wc -l | tr -d ' ')"

if [[ "$STAGED" -eq 0 && "$UNSTAGED" -eq 0 && "$UNTRACKED" -eq 0 ]]; then
    echo -e "  Alterações: ${GREEN}nenhuma — working tree limpa${NC}"
else
    [[ "$STAGED" -gt 0 ]]    && echo -e "  Staged:     ${GREEN}${STAGED} arquivo(s) prontos para commit${NC}"
    [[ "$UNSTAGED" -gt 0 ]]  && echo -e "  Modificados:${YELLOW} ${UNSTAGED} arquivo(s) com alterações não staged${NC}"
    [[ "$UNTRACKED" -gt 0 ]] && echo -e "  Não rastr.: ${GRAY}${UNTRACKED} arquivo(s) não rastreados${NC}"
fi

# Detalhe das alterações
if [[ "$STAGED" -gt 0 || "$UNSTAGED" -gt 0 || "$UNTRACKED" -gt 0 ]]; then
    echo ""
    git status --short | sed 's/^/    /'
fi

sep

# Últimos commits
echo -e "  ${BOLD}Últimos commits:${NC}"
git log --oneline -5 | sed 's/^/    /'

sep

# Stashes
STASH_COUNT="$(git stash list | wc -l | tr -d ' ')"
if [[ "$STASH_COUNT" -gt 0 ]]; then
    echo -e "  ${YELLOW}Stashes salvos: ${STASH_COUNT}${NC}"
    git stash list | head -5 | sed 's/^/    /'
    sep
fi

# Branches locais
echo -e "  ${BOLD}Branches locais:${NC}"
git branch -v | sed 's/^/    /'

sep
echo ""

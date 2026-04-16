#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "=== Check de prontidão para merge (AgentEscala) ==="

has_error=false

if [[ -n "$(git ls-files -u)" ]]; then
  echo "[ERRO] Existem arquivos em estado de merge não resolvido (git ls-files -u)."
  git ls-files -u
  has_error=true
else
  echo "[OK] Nenhum arquivo em estado de merge pendente (index unmerged)."
fi

printf "\nProcurando marcadores de conflito (<<<<<<<, =======, >>>>>>>) em arquivos versionados...\n"
conflict_hits="$(git grep -n -E '^(<<<<<<<|=======|>>>>>>>)' -- . ':(exclude)package-lock.json' || true)"

if [[ -n "$conflict_hits" ]]; then
  echo "[ERRO] Marcadores de conflito encontrados:"
  echo "$conflict_hits"
  has_error=true
else
  echo "[OK] Nenhum marcador de conflito encontrado em arquivos versionados."
fi

if [[ "$has_error" == true ]]; then
  printf "\nResultado: FALHA — repositório não está pronto para merge.\n"
  exit 1
fi

printf "\nResultado: SUCESSO — repositório pronto para merge (sem conflitos locais detectados).\n"

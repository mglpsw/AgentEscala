# AgentEscala — Workflow Diário no Terminal

Guia prático para trabalhar no AgentEscala via terminal (local, SSH, Termius).

## Início de Sessão

```bash
# Entrar no repo
cd /opt/repos/AgentEscala

# Ver estado geral (branch, alterações, divergência com origin)
./scripts/git-status-summary.sh
```

---

## Atualizar da Main com Segurança

**Quando usar:** ao começar uma nova sessão ou antes de criar uma branch.

```bash
./scripts/git-safe-update.sh
```

O script:
1. Verifica se há alterações locais não commitadas — **para antes de sobrescrever**
2. Faz `git fetch origin` (só download, sem alterar arquivos)
3. Se você estiver na `main`: faz `git merge --ff-only origin/main` (merge conservador, falha se não for fast-forward)
4. Se você estiver em outra branch: mostra a divergência e propõe o próximo passo

**Por que merge e não rebase na main?**
O `--ff-only` é o mais seguro possível: só avança se não houver divergência. Se falhar, nada muda e você decide o que fazer.

**Se o script detectar alterações locais:**
```bash
# Opção A: salvar como stash e atualizar
git stash push -m "wip: descrição do que estava fazendo"
./scripts/git-safe-update.sh
git stash pop

# Opção B: commitar antes de atualizar
git add <arquivos>
git commit -m "wip: checkpoint antes de atualizar"
./scripts/git-safe-update.sh
```

---

## Trabalhar em Branch Própria

**Regra:** nunca commitar diretamente na `main`.

```bash
# Criar branch a partir da main atualizada
./scripts/git-start-feature.sh feat/nome-da-tarefa

# Ou manualmente
git checkout main
git pull --ff-only origin main
git checkout -b feat/nome-da-tarefa
```

Prefixos de branch:

| Prefixo | Quando usar |
|---------|-------------|
| `feat/` | Nova funcionalidade |
| `fix/` | Correção de bug |
| `refactor/` | Refatoração sem mudança de comportamento |
| `docs/` | Apenas documentação |
| `chore/` | Manutenção, deps, infra |
| `test/` | Adição/correção de testes |

---

## Editar Arquivos Localmente

```bash
# Editar com vim (terminal puro)
vim backend/services/shift_service.py

# Editar com nano (mais simples)
nano backend/routes/shifts.py

# Ver o diff antes de commitar
git diff

# Ver diff de um arquivo específico
git diff backend/services/shift_service.py
```

---

## Revisar Diffs Antes de Commitar

```bash
# Ver o que mudou (não staged)
git diff

# Ver o que está staged para commit
git diff --cached

# Resumo dos arquivos alterados
git diff --stat

# Ver alterações entre sua branch e main
git diff main...HEAD
```

---

## Commitar com Mensagens Limpas

```bash
# Adicionar arquivos específicos (preferível ao git add .)
git add backend/services/shift_service.py
git add backend/routes/shifts.py

# Commitar com mensagem semântica
git commit -m "feat: adiciona validação de conflito de turno duplo"

# Ver o que foi commitado
git log --oneline -5
```

**Padrão de mensagem (Conventional Commits):**
```
<tipo>: <descrição curta no imperativo>

Tipos: feat, fix, refactor, docs, chore, test
Exemplos:
  feat: adiciona parser OCR para PDF de escala
  fix: corrige validação de conflito de plantão
  docs: atualiza instruções de deploy no homelab
  chore: atualiza dependências do requirements.txt
```

---

## Validar Backend e Frontend

```bash
# Testes automatizados do backend
cd /opt/repos/AgentEscala
python -m pytest tests/ -v

# Teste rápido de um módulo específico
python -m pytest tests/test_shift_service.py -v

# Verificar saúde da API em produção
curl -s https://escala.ks-sm.net:9443/api/health | jq .

# Verificar API local (dev)
curl -s http://192.168.3.155:18000/api/health | jq .

# Build do frontend (verifica erros de compilação)
cd frontend && npm run build && cd ..

# Lint do backend (se configurado)
cd /opt/repos/AgentEscala && python -m flake8 backend/ --max-line-length=120
```

---

## Evitar Sobrescrições Acidentais

**Antes de qualquer edição destrutiva:**

```bash
# Ver estado completo antes de agir
git status
git stash list

# Fazer backup de um arquivo antes de editar
cp backend/services/shift_service.py backend/services/shift_service.py.bak

# Verificar se há stashes salvos
git stash list

# Recuperar um stash específico sem aplicar (só ver)
git stash show stash@{0} -p
```

**Se você sobrescreveu algo por acidente:**

```bash
# Recuperar versão do último commit (descarta alterações locais desse arquivo)
git checkout HEAD -- backend/services/shift_service.py

# Recuperar versão de um commit específico
git checkout <hash-do-commit> -- <arquivo>

# Ver histórico de um arquivo
git log --oneline -- backend/services/shift_service.py
```

---

## Preparar PR Limpo

```bash
# 1. Garantir que sua branch está atualizada com main
git fetch origin
git log --oneline main..HEAD    # commits só na sua branch
git diff main...HEAD --stat     # resumo das mudanças

# 2. Organizar commits se necessário (squash de commits WIP)
# CUIDADO: só fazer isso se os commits ainda não foram enviados ao remoto
git rebase -i main

# 3. Push da branch para GitHub
git push origin feat/nome-da-tarefa

# 4. Criar PR via gh CLI
gh pr create \
  --title "feat: descrição curta" \
  --body "$(cat <<'EOF'
## O que faz
- Descreva a mudança principal

## Como testar
- Passo 1
- Passo 2

## Riscos
- Liste riscos conhecidos ou deixe "Nenhum"
EOF
)"

# 5. Ver PRs abertos
gh pr list

# 6. Ver status de checks do PR
gh pr checks
```

---

## Situações de Conflito

**Se `git pull` ou `git merge` gerou conflito:**

```bash
# Ver os arquivos em conflito
git status

# Editar cada arquivo conflitante (resolver <<<<< ===== >>>>>)
vim <arquivo-em-conflito>

# Após resolver, marcar como resolvido
git add <arquivo-resolvido>

# Finalizar o merge
git commit

# Se quiser abortar e voltar ao estado anterior
git merge --abort
```

**Se você está no meio de um rebase e deu conflito:**

```bash
# Resolver o conflito no arquivo
vim <arquivo>
git add <arquivo>
git rebase --continue

# Ou abortar e voltar ao estado anterior
git rebase --abort
```

---

## Rebuild de Produção

```bash
# ÚNICA forma segura de rebuild
./infra/scripts/rebuild_official_homelab.sh

# Com alterações locais intencionais não commitadas
./infra/scripts/rebuild_official_homelab.sh --allow-dirty

# NUNCA usar:
# docker-compose up -d --build   ← cria stack errada (não oficial)
```

---

## Comandos do Dia a Dia (Cheatsheet)

```bash
# Estado geral
./scripts/git-status-summary.sh

# Atualizar da main
./scripts/git-safe-update.sh

# Nova branch de trabalho
./scripts/git-start-feature.sh feat/minha-tarefa

# Ver o que mudou
git diff
git diff --stat

# Commitar
git add <arquivo>
git commit -m "feat: descrição"

# Enviar para GitHub
git push origin HEAD

# Criar PR
gh pr create --title "feat: ..." --body "..."

# Saúde da API
curl -s https://escala.ks-sm.net:9443/api/health | jq .

# Rodar testes
python -m pytest tests/ -v
```

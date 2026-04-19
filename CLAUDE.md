# AgentEscala — Instruções para Claude Code CLI

## Contexto do Projeto

Sistema de automação de escalas médicas. Stack: FastAPI + React + PostgreSQL.
Roda no homelab (CT102). Acesso externo: `https://escala.ks-sm.net:9443`.

Dentro do CT102, valide o NPM por `https://escala.ks-sm.net` e o backend por
`http://192.168.3.155:18000`. A porta `9443` fica na borda do roteador/firewall
e não deve ser usada como verificação interna única.

Clone canônico: `/opt/repos/AgentEscala`
Compose canônico: `infra/docker-compose.homelab.yml`
Stack canônica: `agentescala_official`

## Regras Obrigatórias

- Sempre responder e documentar em **português do Brasil**
- Nunca fazer push direto para `main` — trabalhar sempre em branch
- Nunca usar `docker-compose up -d --build` na raiz — usar `./infra/scripts/rebuild_official_homelab.sh`
- Nunca sobrescrever arquivos sensíveis sem mostrar diff antes
- Nunca quebrar serviços em produção (compose, proxies, banco de dados)
- Mudanças pequenas, testáveis e reversíveis — sem grandes reestruturações
- Em dúvida: escolher sempre a solução conservadora

## Agent Terminal (agent-router local)

O repo tem um agent LLM integrado que usa o **agent-router** do homelab como backend.
Não depende de créditos Anthropic/OpenAI — usa os LLMs locais e externos via router.

```bash
# Sessão interativa (edita arquivos, lê repo, commita com git)
./scripts/agent.sh

# Consulta rápida sem editar arquivos
./scripts/agent.sh -q "como funciona o shift_service?"

# Usar modelo específico
./scripts/agent.sh -m agent-router:aiops "refatore o shift_service"
./scripts/agent.sh -m agent-router:gpt-external "revisar PR"   # via OpenAI
./scripts/agent.sh -m chat:raciocinio "analise a arquitetura"

# Ver modelos disponíveis
./scripts/agent.sh -l

# De fora da rede (Termius, externo)
./scripts/agent.sh --external -q "status do repo"

# Consulta rápida via llm CLI
OPENAI_API_KEY=dummy llm --no-stream -m "agent-router/chat:rapido" "sua pergunta"
```

**Agent-router:**

- Interno: `http://192.168.3.155:8010` (auto-detectado)
- Externo: `https://api.ks-sm.net:9443` (flag `--external` ou var `AGENT_URL`)
- Sem autenticação internamente

**Modelos principais:**

| Modelo                      | Uso                                |
| --------------------------- | ---------------------------------- |
| `chat:codigo`               | Edição de código (padrão do aider) |
| `chat:rapido`               | Consultas rápidas                  |
| `chat:raciocinio`           | Arquitetura e análise              |
| `agent-router:aiops`        | Decisão automática de roteamento   |
| `agent-router:gpt-external` | OpenAI via router                  |

## Workflow Git Diário

```bash
# 1. Ver estado atual
./scripts/git-status-summary.sh

# 2. Atualizar da main com segurança
./scripts/git-safe-update.sh

# 3. Criar branch de trabalho
./scripts/git-start-feature.sh feat/nome-da-tarefa

# 4. Trabalhar, commitar (commits pequenos e semânticos)
git add <arquivos>
git commit -m "feat: descrição curta e clara"

# 5. Push opcional para GitHub
git push origin HEAD

# 6. Abrir PR via gh (opcional)
gh pr create --title "feat: ..." --body "..."
```

## Convenção de Branches

| Prefixo | Uso |
|---------|-----|
| `feat/` | Nova funcionalidade |
| `fix/` | Correção de bug |
| `refactor/` | Refatoração sem mudança de comportamento |
| `docs/` | Documentação |
| `chore/` | Manutenção, deps, infra |
| `test/` | Testes |

## Padrão de Commits (Conventional Commits)

```
feat: adiciona parser OCR para PDF de escala
fix: corrige validação de conflito de plantão
refactor: extrai lógica de troca para swap_service
docs: atualiza README com instruções de deploy
chore: atualiza dependências do requirements.txt
test: adiciona testes para shift_service
```

## Estrutura do Projeto

```
backend/          FastAPI — rotas, modelos, migrations (Alembic)
backend/services/ Lógica de negócio
frontend/         React — interface web
infra/            Docker Compose, scripts de deploy/homelab
scripts/          Scripts utilitários de desenvolvimento
docs/             Documentação técnica e operacional
tests/            Testes automatizados
reports/          Relatórios gerados por agentes
```

## Arquivos Sensíveis — Nunca Sobrescrever Sem Revisar

- `infra/.env.homelab` — variáveis de ambiente de produção (nunca exibir segredos)
- `infra/docker-compose.homelab.yml` — compose de produção
- `backend/alembic/versions/` — migrations do banco de dados
- `docker-compose.yml` — compose local de desenvolvimento

## Validação Backend/Frontend

```bash
# Backend: rodar testes
cd /opt/repos/AgentEscala && python -m pytest tests/ -v

# Backend: verificar API a partir do CT102
curl -sk https://escala.ks-sm.net/health | jq .

# Backend local (dev)
curl -s http://192.168.3.155:18000/health | jq .

# Frontend: build local
cd frontend && npm run build
```

`infra/.env.homelab` ativo nunca deve ficar com placeholders `CHANGE_ME_*`; isso
fica restrito ao `.env.homelab.example`.

## Rebuild de Produção

```bash
# Rebuild oficial (única forma segura)
./infra/scripts/rebuild_official_homelab.sh

# Se houver alterações locais intencionais não commitadas
./infra/scripts/rebuild_official_homelab.sh --allow-dirty
```

## Documentação Relacionada

- [Workflow no Terminal](docs/workflow-terminal.md)
- [Deploy no Homelab](docs/homelab_deploy.md)
- [Instruções Git](/.github/instructions/agentescala-git.instructions.md)
- [Instruções Gerais](/.github/instructions/agentescala-geral.instructions.md)

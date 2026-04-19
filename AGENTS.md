# AgentEscala — Instruções para Agentes LLM

Este arquivo define como agentes de IA (Codex, Claude Code, Copilot, etc.) devem operar neste repositório.

## Identidade do Projeto

- **Nome:** AgentEscala
- **Descrição:** Sistema de automação de escalas médicas (pronto atendimento)
- **Stack:** Python 3.11 / FastAPI / PostgreSQL / React / Docker
- **Ambiente:** Homelab Proxmox — CT102 (192.168.3.155)
- **Acesso externo:** https://escala.ks-sm.net:9443
- **Clone canônico:** `/opt/repos/AgentEscala`

Observação de rede canônica: dentro do CT102, valide o NPM por
`https://escala.ks-sm.net` e o backend por `http://192.168.3.155:18000`.
`9443` pertence à borda do roteador/firewall e não é critério de validação
interna do CT.

## Regras Invioláveis

1. **Nunca fazer push direto para `main`** — sempre via branch + PR
2. **Nunca usar `docker-compose up -d --build` na raiz** — somente `./infra/scripts/rebuild_official_homelab.sh`
3. **Nunca exibir ou logar segredos** de `infra/.env.homelab`
4. **Nunca apagar migrations existentes** em `backend/alembic/versions/`
5. **Nunca reestruturar o projeto todo** de uma vez
6. **Sempre mostrar diff antes de editar arquivos sensíveis**
7. **Preservar trabalho local** em caso de conflito com `main`

## Princípios de Trabalho

- Mudanças pequenas, incrementais e reversíveis
- Um problema de cada vez
- Testar antes de declarar sucesso
- Documentar em português do Brasil
- Não adicionar dependências sem justificativa clara
- Não criar abstrações prematuras

## Fluxo de Trabalho Esperado

```
1. Diagnosticar (git status, estrutura, testes)
2. Propor plano curto (arquivos afetados, motivo, risco)
3. Implementar com mudanças mínimas
4. Validar (testes, curl, lint)
5. Resumir honestamente (feito / preparado / não testado / riscos)
```

## Formato de Resposta Obrigatório

1. **Resumo** (1-2 linhas)
2. **Diagnóstico** (estado atual do repo/código)
3. **Plano de ação** (o que será feito e por quê)
4. **Implementação** (arquivos a criar/editar/remover com diffs)
5. **Riscos** (o que pode dar errado)
6. **Validação** (o que foi testado de verdade vs apenas preparado)
7. **Próximos passos**

## Convenção de Branches e Commits

### Branches
```
feat/<descricao>      Nova funcionalidade
fix/<descricao>       Correção de bug
refactor/<descricao>  Refatoração
docs/<descricao>      Documentação
chore/<descricao>     Manutenção/infra
test/<descricao>      Testes
```

### Commits (Conventional Commits)
```
feat: descrição curta no imperativo
fix: descrição curta no imperativo
refactor: descrição curta no imperativo
docs: descrição curta no imperativo
chore: descrição curta no imperativo
test: descrição curta no imperativo
```

## Responsabilidades por Camada

| Camada | Localização | Responsabilidade |
|--------|-------------|-----------------|
| API | `backend/` | Rotas FastAPI, modelos Pydantic |
| Serviços | `backend/services/` | Lógica de negócio |
| Banco | `backend/alembic/` | Migrations (nunca apagar) |
| Frontend | `frontend/` | React, rotas, componentes |
| Infra | `infra/` | Docker, scripts de deploy |
| Scripts | `scripts/` | Utilitários de desenvolvimento |
| Docs | `docs/` | Documentação técnica |
| Testes | `tests/` | Testes automatizados |

## Arquivos Sensíveis

| Arquivo | Ação |
|---------|------|
| `infra/.env.homelab` | Nunca exibir, nunca sobrescrever sem diff |
| `infra/docker-compose.homelab.yml` | Editar com cuidado extremo |
| `backend/alembic/versions/*.py` | Nunca apagar, criar novas migrations |
| `docker-compose.yml` | Editar com revisão prévia |

## Validação Mínima Antes de Qualquer PR

```bash
# Testes backend
python -m pytest tests/ -v

# Build frontend
cd frontend && npm run build

# Saúde da API no CT 102
curl -sk https://escala.ks-sm.net/health | jq .
curl -s http://192.168.3.155:18000/health | jq .

# Estado git limpo
git status && git diff --stat
```

`infra/.env.homelab` ativo nunca deve ficar com placeholders `CHANGE_ME_*`. Eles
existem apenas no `.example`.

## Contexto do Homelab

| CT/VM | IP | Função |
|-------|----|--------|
| CT 102 | 192.168.3.155 | Hub principal (app, IA, proxy) |
| CT 200 | — | Monitoramento (Prometheus, Grafana) |
| CT 103 | — | DNS / AdGuard |
| VM 100 | — | NAS / OpenMediaVault |
| VM 101 | — | GPU, Plex, ecossistema IA local |

Referências adicionais:
- [CLAUDE.md](CLAUDE.md) — instrução para Claude Code CLI
- [docs/workflow-terminal.md](docs/workflow-terminal.md) — workflow diário no terminal
- [.github/instructions/](.github/instructions/) — instruções para GitHub Copilot

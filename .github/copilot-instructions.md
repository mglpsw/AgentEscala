# AgentEscala — Instruções Copilot / Codex

## Visão Geral
Projeto de backend inteligente para gestão de escalas médicas.

Integra com:
- API do Homelab (AIOps Orchestrator)
- Agent Router (roteamento LLM)
- OCR de escalas
- Backend FastAPI

## Integração com Homelab

- API: https://api.ks-sm.net:9443
- Auth: Bearer Token (HOMELAB_API_TOKEN)
- SSL: self-signed (usar verify=False)

## Endpoints úteis

- GET /health
- GET /v1/providers/status
- POST /v1/chat/ingest
- GET /v1/tasks
- GET /metrics

## Regras de uso

- Sempre priorizar @ollama para tarefas simples
- Usar @codex para código
- Usar @claude para arquitetura complexa
- Nunca executar ações destrutivas sem confirmação

## Fluxo padrão

1. Diagnosticar via /health
2. Ver providers
3. Enviar tarefa para /chat/ingest
4. Val

idar retoeno

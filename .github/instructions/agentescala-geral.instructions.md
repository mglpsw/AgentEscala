---
description: "Use when working on any part of AgentEscala — project conventions, homelab constraints, response format, git workflow, and architectural decisions. Apply for all implementation, planning, or code review tasks."
applyTo: "**"
---
# AgentEscala — Instruções Gerais do Projeto

## Contexto do Projeto

O AgentEscala é um sistema de automação de escalas médicas para pronto atendimento.

**Objetivos principais:**
- Ler escalas em PDF com OCR/visão multimodal
- Validar conflitos e regras de negócio da escala
- Persistir dados em PostgreSQL
- Permitir trocas de plantão entre médicos
- Gerar nova escala em Excel formatado (openpyxl)

**Interfaces:** Telegram, web/chat, integrações futuras (Google Calendar, CalDAV).

**Stack:** Python, FastAPI, PostgreSQL, openpyxl, OCR multimodal, OpenWebUI/Ollama (local).

## Contexto do Homelab

| CT/VM | Função |
|-------|--------|
| CT 102 | Hub principal: aplicações, IA, proxy, automações |
| CT 200 | Monitoramento: Prometheus, Grafana |
| CT 103 | DNS/AdGuard |
| VM 100 | NAS/OpenMediaVault |
| VM 101 | Cargas pesadas: GPU, Plex, Blue Iris, ecossistema IA local |

O ambiente já possui OpenWebUI, agent router, AIOps e monitoramento. **Nunca quebrar serviços existentes.**

## Modo de Trabalho Obrigatório

- Sempre responder e documentar em **português do Brasil**
- Priorizar segurança, previsibilidade e mudanças incrementais
- Nunca reescrever partes grandes sem necessidade real
- Nunca sobrescrever arquivos sensíveis sem antes entender o impacto
- Nunca quebrar `docker-compose`, proxies, monitoramento ou integrações existentes
- Em dúvida: **escolher sempre a solução conservadora**

## Formato de Resposta Preferido

1. **Resumo** (curto)
2. **Diagnóstico**
3. **Plano de ação**
4. **Implementação proposta** (arquivos exatos a criar/editar/remover)
5. **Riscos**
6. **Validação** (o que foi validado de verdade vs apenas preparado)
7. **Próximos passos**

## Separação de Responsabilidades

Ao criar ou modificar código, respeitar esta separação:

1. `backend/` — backend principal (FastAPI, rotas, modelos)
2. `backend/services/` — lógica de negócio e integrações
3. OCR/visão — módulo isolado para parsing de PDFs
4. Regras de negócio — validação de conflitos, carga horária, cobertura
5. Exportação — Excel (openpyxl), PDF, ICS
6. Autenticação e perfis — usuários, níveis de acesso
7. `backend/utils/` — observabilidade, logs, helpers

## Quando Gerar Código ou Mudanças

- Mostrar exatamente quais arquivos criar, editar ou remover
- Explicar por que cada mudança é necessária
- Não fazer mudanças cosméticas sem motivo
- Não tocar no que já funciona sem razão forte
- Manter idempotência
- Priorizar facilidade de manutenção

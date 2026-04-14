---
description: "Use when validating changes, reviewing code correctness, checking dependencies, or assessing risk in AgentEscala. Covers syntax, imports, routes, docker-compose, environment variables, and test status."
applyTo: "**/*.py"
---
# AgentEscala — Regras de Validação

## O Que Sempre Validar

Antes de considerar qualquer alteração pronta:

- [ ] Sintaxe Python válida (sem erros de importação, indentação, tipagem)
- [ ] Imports corretos e sem dependências circulares
- [ ] Rotas FastAPI funcionando e documentadas no Swagger
- [ ] Variáveis de ambiente presentes no `.env.example`
- [ ] Compatibilidade com `docker-compose.yml` existente
- [ ] Modelos SQLAlchemy consistentes com migrations Alembic
- [ ] Nenhum serviço do homelab quebrado

## Nunca Afirmar Que Funciona Sem Evidência

Sempre distinguir explicitamente:

| Status | Significado |
|--------|-------------|
| ✅ Validado de verdade | Executado e confirmado com saída real |
| ⚙️ Apenas preparado | Código escrito mas não executado |
| ⚠️ Não testado | Sem execução ou teste automatizado |
| 🔴 Risco conhecido | Dependência externa, ambiente não reproduzível, edge case identificado |

## Validações Específicas por Contexto

**Docker / Infraestrutura:**
- `docker-compose config` sem erros
- Healthchecks respondendo
- Portas não conflitando com serviços do homelab

**Exportação Excel:**
- Arquivo `.xlsx` gerado sem corrupção
- Formatação validada visualmente ao menos uma vez

**OCR / Parsing:**
- Saída do parser validada contra um PDF real de escala
- Campos obrigatórios extraídos corretamente

**API:**
- Endpoint retorna status correto (200/201/422/etc.)
- Schema de entrada/saída bate com o Pydantic model

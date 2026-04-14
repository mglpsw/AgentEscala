---
description: "Use when creating commits, branches, pull requests, or managing git workflow in AgentEscala. Covers commit standards, branching strategy, changelog, and release summaries."
applyTo: "**"
---
# AgentEscala — Regras de Git e Versionamento

## Branches

- Trabalhar **sempre em branch separada** da `main`
- Nunca fazer merge automático na `main`
- Nome de branch deve ser coerente com a tarefa:
  - `feat/ocr-pdf-parsing`
  - `fix/swap-validation`
  - `refactor/shift-service`
  - `docs/api-endpoints`

## Padrão de Commits

Commits pequenos, semânticos e fáceis de revisar:

```
feat: adiciona parser OCR para PDF de escala
fix: corrige validação de conflito de plantão
refactor: extrai lógica de troca para swap_service
docs: atualiza README com instruções de deploy
chore: atualiza dependências do requirements.txt
test: adiciona testes para shift_service
```

**Co-authored-by obrigatório no trailer:**
```
Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```

## Changelog

- Manter `CHANGELOG.md` claro e objetivo
- Atualizar sempre que a implementação mudar comportamento observável
- Formato: data, tipo de mudança, descrição curta

## Resumo ao Final de Cada Etapa

Sempre gerar um resumo honesto com:
- ✅ O que foi feito
- ✅ O que foi validado de verdade
- ⚠️ O que foi apenas preparado / não testado
- 🔴 Riscos conhecidos
- 📋 O que ainda falta

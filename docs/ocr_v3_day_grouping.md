# OCR v3 — Parsing determinístico agrupado por dia

## Objetivo
Reduzir dependência de LLM/tokens no import documental, priorizando parsing local auditável.

## Pipeline
1. Detecta layout (`avive_tabular`, `pa24h_block`, `generic_table`).
2. Limpa nome (telefone, `Faturamento`, ruído), normaliza e aplica aliases configuráveis.
3. Faz match local (nome + alias + CRM + coerência de padrão histórico).
4. Valida por dia (CRM ausente, ambiguidades, turnos duplicados etc.).
5. Apenas marca fallback opcional para LLM quando houver baixa confiança/ambiguidade.

## Formato canônico expandido
Cada linha normalizada agora pode carregar: `source_layout_type`, `day_group_id`, `schedule_pattern_type`, `canonical_name`, `crm_detected`, `crm_confidence`, `alias_applied`, `shift_kind`, `multiple_professionals_detected`, `grouped_day_validation`, `suggested_existing_user_id`, `suggested_profile_enrichment`, `llm_fallback_recommended`.

## UI Admin
A preview OCR mostra cards por dia com:
- layout detectado
- alertas do dia
- score médio
- edição inline mínima de nome e horários
- painel lateral com indicadores de conflito e enriquecimento CRM

## Compatibilidade
Fluxo legado preservado:
`parse -> preview -> apply-to-staging -> revisão -> confirmação`.

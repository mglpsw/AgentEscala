---
description: "Use when adding logging, metrics, healthchecks, monitoring or audit trails to AgentEscala. Covers Prometheus integration, Grafana dashboards, OCR observability, and audit logging for critical automations."
applyTo: "**/*.py"
---
# AgentEscala — Observabilidade e Logs

## Princípio

Tudo operacionalmente relevante deve ser **observável**. Nunca adicionar lógica crítica sem log ou métrica associada.

## O Que Sempre Instrumentar

| Componente | O que observar |
|------------|----------------|
| OCR/parsing | Tempo de processamento, taxa de falha, campos não extraídos |
| Importação de PDF | Status (sucesso/falha), motivo de erro, arquivo processado |
| Geração de Excel | Tempo, linhas geradas, erros de formatação |
| Trocas de plantão | Quem pediu, aprovação/rejeição, timestamp |
| API | Tempo de resposta, status HTTP, erros 4xx/5xx |
| Tarefas assíncronas | Status da fila, retries, falhas permanentes |

## Padrão de Log

```python
import logging
logger = logging.getLogger(__name__)

# Use níveis adequados:
logger.info("Escala importada com sucesso: %s", filename)
logger.warning("Campo 'médico' não encontrado na linha %d", line_num)
logger.error("Falha ao gerar Excel: %s", str(e), exc_info=True)
```

## Métricas (Prometheus-ready)

Prever labels e nomes de métrica compatíveis com Prometheus/Grafana (CT 200):

```python
# Exemplo de contadores úteis:
# agentescala_pdf_imports_total{status="success|failure"}
# agentescala_excel_exports_total{status="success|failure"}
# agentescala_ocr_duration_seconds
# agentescala_swap_requests_total{status="approved|rejected"}
```

## Healthchecks

Todo serviço exposto deve ter `/health` respondendo:

```python
@router.get("/health")
def health():
    return {"status": "ok", "service": "agentescala"}
```

## Trilha de Auditoria

Para operações críticas (aprovação de troca, geração de escala, importação):

```python
# Registrar: quem fez, quando, o que mudou, resultado
audit_log(user_id=user.id, action="swap_approved", details={...})
```

## Integração Futura com CT 200

- Expor métricas via `/metrics` (formato Prometheus)
- Usar nomes de métricas com prefixo `agentescala_`
- Documentar no `docs/` quais métricas existem e o que representam

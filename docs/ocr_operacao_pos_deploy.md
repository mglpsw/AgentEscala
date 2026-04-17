# Operação OCR pós-deploy (release 1.5.1 consolidada)

Guia curto para validar OCR com segurança em ambiente homelab/CT 102, preservando o comportamento atual.

## 1) Validar saúde geral

```bash
curl -sS http://localhost:8000/health
```

Esperado:
- `status` = `healthy` (ou `degraded` se banco indisponível).
- `ocr` = `enabled` ou `disabled` conforme configuração ativa.

## 2) Validar configuração efetiva do OCR

```bash
curl -sS http://localhost:8000/api/v1/info
```

No bloco `ocr`, conferir:
- `api_enabled`
- `api_base_url`
- `api_timeout_seconds`
- `api_verify_ssl`

## 3) Interpretar estratégia de execução

- `strategy=api`: OCR atendido pela API externa.
- `strategy=fallback_local`: OCR local acionado por falha/indisponibilidade da API externa.

Logs estruturados esperados no backend:
- sucesso API: `ocr_execution strategy=api status=success ... latency_ms=...`
- falha API: `ocr_execution strategy=api status=failure ... reason=...`
- fallback local: `ocr_execution strategy=fallback_local status=success fallback_type=... reason=...`

## 4) Validar métricas OCR

```bash
curl -sS http://localhost:8000/metrics | grep -E 'ocr_(requests_total|api_success_total|api_failure_total|fallback_used_total|api_latency_seconds)'
```

Métricas:
- `ocr_requests_total{strategy="api|fallback_local"}`
- `ocr_api_success_total`
- `ocr_api_failure_total`
- `ocr_fallback_used_total{fallback_type="local_pdf|local_image"}`
- `ocr_api_latency_seconds`

## 5) Executar smoke test pós-deploy

Sem autenticação (validação base):

```bash
BASE_URL=http://localhost:8000 bash scripts/smoke_ocr_release.sh
```

Com validação de import OCR autenticada:

```bash
BASE_URL=http://localhost:8000 \
ADMIN_TOKEN='<jwt_admin>' \
OCR_SAMPLE_FILE='tests/fixtures/escala_exemplo.csv' \
bash scripts/smoke_ocr_release.sh
```

> Observação: para OCR real de PDF/imagem, informe um arquivo compatível em `OCR_SAMPLE_FILE`.

## 6) Como saber se a API externa falhou e fallback local entrou

Sinais combinados:
- logs com `strategy=fallback_local`;
- incremento de `ocr_fallback_used_total`;
- incremento de `ocr_requests_total{strategy="fallback_local"}`.

## 7) Limitações atuais (intencionais para estabilidade)

- Não há automação destrutiva para derrubar API externa no smoke test.
- Validação de fallback forçado fica como checklist manual controlado.
- Contratos atuais de `/health` e `/api/v1/info` foram preservados; apenas campos adicionais não disruptivos foram expostos em `/api/v1/info`.

## 8) Revisão rápida de domínio (escala médica)

A validação de escala já cobre no fluxo de importação:
- nomes médicos e matching;
- turnos diurnos/noturnos;
- duplicidade;
- sobreposição;
- duração inválida por regras de jornada.

Nesta consolidação, sem alteração de contrato: apenas reforço operacional (métricas/logs/smoke/documentação).

# ARCHITECTURE — AgentEscala (1.5.1)

## Fluxo completo de escala

```text
entrada (CSV/XLSX/PDF/Imagem)
  -> upload/importação
  -> OCR (somente para PDF/Imagem; API ks-sm prioritária)
  -> fallback local OCR (se necessário)
  -> normalização de dados
  -> validação de domínio (duplicidade/sobreposição/duração)
  -> persistência em staging
  -> confirmação administrativa
  -> persistência final (shifts)
  -> consumo via API
  -> frontend React
```

## Separação de camadas

### 1) Backend FastAPI

- Responsável por auth JWT, usuários, plantões, trocas, importação e validação.
- Mantém staging obrigatório antes da confirmação.
- Expõe endpoints operacionais (`/health`, `/metrics`, `/api/v1/info`).

### 2) Frontend React

- Consome API para login, visualização de calendário e trocas.
- Não aplica regras críticas de domínio; regras permanecem no backend.

### 3) Integração OCR externa (prioritária)

- Base URL padrão: `https://api.ks-sm.net:9443`.
- Configuração via env:
  - `OCR_API_BASE_URL`
  - `OCR_API_TIMEOUT_SECONDS`
  - `OCR_API_ENABLED`
  - `OCR_API_VERIFY_SSL`
- Leitura resiliente de payload OCR (`raw_text`, `text`, `content`, `lines`, `data`, `result`).

### 4) Fallback local OCR (preservado)

- Mantido para continuidade operacional em falhas externas.
- Continua disponível para PDF/imagem sem alterar contratos atuais.
- Não há dependência exclusiva da API externa.

### 5) Observabilidade

- `/health`: status da aplicação, banco, versão e estado resumido de OCR.
- `/metrics`: métricas Prometheus de requisições, importações e domínio.
- `/api/v1/info`: expõe bloco `ocr` para diagnóstico operacional.

### 6) Homelab

- CT 102: execução principal (API, frontend, integrações).
- CT 200: observabilidade (Prometheus/Grafana), quando aplicável.
- Publicação segura via Nginx Proxy Manager com SSL.

## Regras de domínio refletidas no fluxo

- Normalização de nomes de profissionais e campos de data/hora.
- Reconhecimento de turnos padrão diurno/noturno.
- Detecção de sobreposição e duplicidade.
- Bloqueios de duração inválida conforme validação de escala.

## Evolução futura (sem quebrar fluxo atual)

1. Ajustes de calibração OCR com datasets reais.
2. Automação assistida de revisão com rastreabilidade.
3. Integrações de notificação com feature flags.

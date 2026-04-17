# AgentEscala (Release 1.5.1)

Sistema de gestão de escalas médicas com foco em estabilidade operacional, rastreabilidade e evolução incremental segura para ambiente homelab.

## Visão geral

O AgentEscala centraliza o ciclo de escala médica: cadastro de usuários, geração/consulta de plantões, trocas e importação assistida com staging.  
Na release **1.5.1**, o sistema está consolidado com OCR resiliente, observabilidade e versionamento alinhado entre backend e frontend.

## Problema que resolve

Hospitais e clínicas precisam reduzir conflitos de plantão, evitar sobreposição de horários e manter governança sobre alterações. O AgentEscala resolve isso com:

- fluxo administrativo auditável;
- validação antes de persistir no calendário final;
- API e frontend integrados para operação diária.

## Funcionalidades atuais

- Autenticação JWT (login, refresh e rotas protegidas por perfil).
- Gestão de usuários, plantões e solicitações de troca.
- Importação de escala com staging e validação.
- Observabilidade com `/health`, `/metrics` e `/api/v1/info`.
- Frontend React com login, calendário e fluxo de trocas.

## Fluxo de importação (estado real)

```text
Upload
  -> CSV/XLSX: leitura tabular direta
  -> PDF/Imagem: OCR (API ks-sm prioritária)
       -> fallback local seguro em caso de falha/indisponibilidade/payload inesperado
  -> normalização
  -> validação (duplicidade, sobreposição, duração)
  -> staging
  -> confirmação administrativa
  -> persistência final em plantões
```

### Regras de suporte por formato

- **CSV/XLSX:** continuam suportados sem mudança de contrato.
- **PDF/Imagem:** usam OCR.
- **OCR externo prioritário:** `https://api.ks-sm.net:9443`.
- **Fallback local preservado:** nunca depende exclusivamente da API externa.

## Stack tecnológica

- **Backend:** FastAPI, SQLAlchemy, Alembic, Prometheus Client.
- **Frontend:** React + Vite.
- **Banco:** PostgreSQL (homelab/produção), SQLite (execução local controlada).
- **Infra:** Docker Compose, Nginx Proxy Manager (SSL), Prometheus.

## Variáveis de ambiente principais

- `DATABASE_URL`
- `SECRET_KEY`
- `CORS_ALLOW_ORIGINS`
- `METRICS_ENABLED`
- `OCR_API_BASE_URL` (default: `https://api.ks-sm.net:9443`)
- `OCR_API_TIMEOUT_SECONDS`
- `OCR_API_ENABLED`
- `OCR_API_VERIFY_SSL`

## Como rodar localmente

### Opção 1 (recomendada): Docker Compose

```bash
docker-compose up -d
```

Endpoints:
- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Metrics: `http://localhost:8000/metrics`
- Info: `http://localhost:8000/api/v1/info`

### Opção 2: backend + frontend separados

Backend:
```bash
pip install -r backend/requirements.txt
cd backend
alembic upgrade head
uvicorn backend.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Execução em homelab (CT 102)

1. Configurar `.env` com variáveis de OCR e banco.
2. Subir stack Docker.
3. Expor API no Nginx Proxy Manager com SSL.
4. Validar scraping Prometheus em `/metrics`.
5. Verificar `/health` e `/api/v1/info` após startup.

## Observabilidade disponível

- `/health`: status da aplicação, banco, versão e estado resumido do OCR.
- `/metrics`: métricas Prometheus (requisições, importações e domínio).
- `/api/v1/info`: versão da API e bloco de configuração operacional OCR.

## Roadmap realista (próximas fases)

1. Melhorar calibração OCR com base em arquivos reais sem quebrar fallback.
2. Expandir automação assistida para revisão de inconsistências.
3. Integrar notificações operacionais (ex.: Telegram) com feature flags.

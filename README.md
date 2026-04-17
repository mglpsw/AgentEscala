# AgentEscala (Release 1.5.3)

Sistema de gestão de escalas médicas com foco em estabilidade operacional, rastreabilidade e evolução incremental segura para ambiente homelab.

## Visão geral

O AgentEscala centraliza o ciclo de escala médica: cadastro de usuários, geração/consulta de plantões, trocas e importação assistida com staging.  
Na release **1.5.3**, o sistema está consolidado com OCR resiliente, observabilidade e versionamento alinhado entre backend e frontend.

## Problema que resolve

Hospitais e clínicas precisam reduzir conflitos de plantão, evitar sobreposição de horários e manter governança sobre alterações. O AgentEscala resolve isso com:

- fluxo administrativo auditável;
- validação antes de persistir no calendário final;
- API e frontend integrados para operação diária.

## Funcionalidades atuais

- Autenticação JWT (login, refresh e rotas protegidas por perfil).
- Login público disponível em `/auth/login` e alias compatível `/api/auth/login` (sem token).
- Gestão de usuários, plantões e solicitações de troca.
- Área administrativa de usuários (somente admin) com listagem, criação, edição e ativação/desativação.
- Trilha de auditoria administrativa mínima para usuários (criação, edição, status e exclusão), com consulta em `GET /admin/audit/users`.
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

> **Fonte de verdade atual:** `infra/docker-compose.homelab.yml` + `infra/.env.homelab` + `infra/scripts/couple_to_homelab.sh`.

## 🚀 Deploy (homelab / CT 102)

### Pré-requisitos

- Docker Engine ativo no CT 102.
- Docker Compose disponível (`docker compose` ou `docker-compose`).
- Porta dedicada livre para o backend (ex.: `18000`).
- Nginx Proxy Manager já operacional no ambiente.

### Variáveis obrigatórias

Use o template oficial:

```bash
cp infra/.env.homelab.example infra/.env.homelab
```

Preencha no mínimo:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `DATABASE_URL`
- `SECRET_KEY`
- `ADMIN_EMAIL`
- `AGENTESCALA_IMAGE`
- `BACKEND_BIND_ADDRESS`
- `BACKEND_HOST_PORT`
- `POSTGRES_VOLUME_NAME`
- `INTERNAL_NETWORK_NAME`
- `PUBLIC_DOMAIN`
- `PUBLIC_PORT`
- `CORS_ALLOW_ORIGINS`

### Comandos oficiais (ordem única)

```bash
# 1) Dry-run (não aplica mudança)
./infra/scripts/couple_to_homelab.sh --dry-run

# 2) Deploy/build
./infra/scripts/couple_to_homelab.sh --build

# 3) Status dos containers
docker compose -p agentescala -f infra/docker-compose.homelab.yml --env-file infra/.env.homelab ps

# 4) Seed (apenas primeira subida ou reset planejado)
docker compose -p agentescala -f infra/docker-compose.homelab.yml --env-file infra/.env.homelab exec backend python -m backend.seed
```

### Validação pós-deploy

```bash
curl -fsS http://127.0.0.1:18000/health
curl -fsS http://127.0.0.1:18000/api/v1/info
```

Checklist funcional mínimo:

1. Login em `/auth/login` (ou `/api/auth/login`) responde 200 com credencial válida.
2. Endpoint admin (`/admin/users` ou `/admin/audit/users`) retorna 200 com token admin.
3. OCR:
   - importação PDF/imagem funciona com API externa **ou**
   - fallback local entra em ação sem quebrar o fluxo.

### Arquivos efetivamente usados no deploy homelab

- `infra/docker-compose.homelab.yml` (stack alvo CT 102).
- `infra/.env.homelab` (variáveis do ambiente).
- `infra/scripts/couple_to_homelab.sh` (orquestração segura com dry-run e rollback local).
- `Dockerfile` (build backend + frontend dist).

### Arquivos legados/movidos (não usados no runtime)

- `infra/legacy/docker-compose.homelab.yml.bak`
- `infra/legacy/COMMIT_MSG_fallback_spa_nginx.txt`
- `infra/legacy/COMMIT_MSG_nginx_9443_spa.txt`

Esses arquivos foram mantidos em `infra/legacy/` para rastreabilidade histórica, sem impacto no deploy atual.

## Observabilidade disponível

- `/health`: status da aplicação, banco, versão e estado resumido do OCR.
- `/metrics`: métricas Prometheus (requisições, importações e domínio).
- `/api/v1/info`: versão da API e bloco de configuração operacional OCR.

## 🧠 Arquitetura real do sistema

Fluxo atual em produção/homelab:

1. Cliente acessa o backend FastAPI (porta publicada no CT 102).
2. FastAPI expõe API REST e também serve o frontend buildado (`frontend/dist`) quando disponível.
3. Banco PostgreSQL roda no mesmo compose homelab, em rede interna dedicada.
4. OCR de PDF/imagem prioriza API externa (`OCR_API_BASE_URL`) e mantém fallback local obrigatório.
5. Autenticação é JWT; endpoints administrativos exigem perfil admin (`role=admin` ou `is_admin=true`).
6. Métricas Prometheus saem em `/metrics`; saúde em `/health`; versão/config operacional em `/api/v1/info`.

Pontos críticos:

- Build frontend deve existir no container (`Dockerfile` faz build multi-stage).
- Migrações Alembic são aplicadas no startup do backend.
- Sem `.env.homelab` válido, o deploy não inicia (falha rápida e explícita).
- Se OCR externo estiver indisponível, fallback local deve manter continuidade operacional.

## Roadmap realista (próximas fases)

1. Melhorar calibração OCR com base em arquivos reais sem quebrar fallback.
2. Expandir automação assistida para revisão de inconsistências.
3. Integrar notificações operacionais (ex.: Telegram) com feature flags.

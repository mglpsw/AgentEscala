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
- **OCR externo prioritário:** `http://192.168.3.155:8010`.
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
- `OCR_API_BASE_URL` (default: `http://192.168.3.155:8010`)
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

## Execução Em Homelab (CT 102)

> **Fonte de verdade atual no CT 102:** clone em `/opt/repos/AgentEscala`, stack Docker `agentescala_official`, `infra/docker-compose.homelab.yml` e `infra/.env.homelab`.

## Deploy Canônico (homelab / CT 102)

### Pré-requisitos

- Docker Engine ativo no CT 102.
- Docker Compose disponível (`docker compose` ou `docker-compose`).
- Porta dedicada do backend no host: `192.168.3.155:18000`.
- Nginx Proxy Manager já operacional no CT 102 em `443`.
- Port-forward externo do roteador: `9443 externo -> CT 102:443`.

### Mapa operacional validado

```text
Cliente externo
  -> https://escala.ks-sm.net:9443
  -> roteador encaminha para CT 102:443
  -> NPM no CT 102 encaminha para http://192.168.3.155:18000
  -> backend AgentEscala no container escuta em 8030
```

Dentro do CT 102, **não há listener em `9443`**. Use `https://escala.ks-sm.net` para testar o NPM local ou `http://192.168.3.155:18000` para testar o backend direto.

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
- `PUBLIC_BASE_URL`
- `VITE_API_BASE_URL`
- `CORS_ALLOW_ORIGINS`

Valores operacionais esperados no CT 102:

```text
COMPOSE_PROJECT_NAME=agentescala_official
PUBLIC_DOMAIN=escala.ks-sm.net
PUBLIC_PORT=9443
PUBLIC_BASE_URL=https://escala.ks-sm.net:9443
VITE_API_BASE_URL=https://escala.ks-sm.net:9443
BACKEND_BIND_ADDRESS=192.168.3.155
BACKEND_HOST_PORT=18000
POSTGRES_VOLUME_NAME=agentescala_postgres_data_official18000
INTERNAL_NETWORK_NAME=agentescala_official_internal
```

### Primeira subida

```bash
cd /opt/repos/AgentEscala
cp infra/.env.homelab.example infra/.env.homelab
nano infra/.env.homelab

./infra/scripts/couple_to_homelab.sh --dry-run
./infra/scripts/couple_to_homelab.sh --build
```

### Atualização de stack já ativo

Quando o backend oficial já está rodando, a porta `18000` estará ocupada pelo próprio AgentEscala. Nesse caso, use o fluxo de atualização validado:

```bash
cd /opt/repos/AgentEscala
git fetch origin main
git merge --ff-only FETCH_HEAD

DEBUG=false docker-compose -p agentescala_official \
  -f infra/docker-compose.homelab.yml \
  --env-file infra/.env.homelab \
  up -d --build --force-recreate backend
```

O `DEBUG=false` é intencional: alguns shells do CT exportam `DEBUG=release`, mas o backend espera booleano.

Status:

```bash
docker-compose -p agentescala_official \
  -f infra/docker-compose.homelab.yml \
  --env-file infra/.env.homelab ps
```

### Validação pós-deploy

```bash
curl -fsS http://192.168.3.155:18000/health
curl -kfsS https://escala.ks-sm.net/health
curl -kfsS https://escala.ks-sm.net/api/v1/info
```

Checklist funcional mínimo:

1. `/` e `/login` retornam o `index.html` do frontend.
2. Bundle frontend contém `https://escala.ks-sm.net:9443`.
3. Preflight CORS de `Origin: https://escala.ks-sm.net:9443` retorna `access-control-allow-origin` correto.
4. Login em `/auth/login` ou `/api/auth/login` responde 200 com credencial válida.
5. Endpoint admin (`/admin/users`, `/api/admin/users` ou `/admin/audit/users`) retorna 401 sem token e 200 com token admin.
6. OCR:
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

## Arquitetura Real Do Sistema

Fluxo atual em produção/homelab:

1. Cliente acessa `https://escala.ks-sm.net:9443`.
2. O roteador entrega a conexão no NPM do CT 102 em `443`.
3. NPM encaminha para `http://192.168.3.155:18000`.
4. FastAPI expõe API REST e também serve o frontend buildado (`frontend/dist`).
5. Banco PostgreSQL roda no mesmo compose homelab, em rede interna dedicada.
6. OCR de PDF/imagem prioriza API externa (`OCR_API_BASE_URL`) e mantém fallback local obrigatório.
7. Autenticação é JWT; endpoints administrativos exigem perfil admin (`role=admin` ou `is_admin=true`).
8. Métricas Prometheus saem em `/metrics`; saúde em `/health`; versão/config operacional em `/api/v1/info`.

Pontos críticos:

- Build frontend deve existir no container (`Dockerfile` faz build multi-stage).
- `VITE_API_BASE_URL` deve ser `https://escala.ks-sm.net:9443`, pois é a origem vista pelo navegador externo.
- Migrações Alembic são aplicadas no startup do backend.
- Sem `.env.homelab` válido, o deploy não inicia (falha rápida e explícita).
- Se OCR externo estiver indisponível, fallback local deve manter continuidade operacional.

## Roadmap realista (próximas fases)

1. Melhorar calibração OCR com base em arquivos reais sem quebrar fallback.
2. Expandir automação assistida para revisão de inconsistências.
3. Integrar notificações operacionais (ex.: Telegram) com feature flags.

# Guia De Deploy Em Homelab

Este guia descreve o deploy canônico do AgentEscala no CT 102. Ele reflete o
estado validado em produção local no CT, preservando isolamento, rollback e
convivência com os demais serviços do homelab.

## Topologia Canônica Do CT 102

Fonte de verdade:

- Clone ativo: `/opt/repos/AgentEscala`
- Stack Docker ativo: `agentescala_official`
- Compose: `infra/docker-compose.homelab.yml`
- Env local: `infra/.env.homelab`
- Backend publicado no host: `192.168.3.155:18000`
- Porta interna do container backend: `8030`
- NPM no CT 102: escuta em `80`, `81` e `443`
- Porta externa `9443`: pertence ao roteador/firewall, não ao CT

Fluxo externo:

```text
Cliente externo
  -> https://escala.ks-sm.net:9443
  -> roteador/firewall encaminha 9443 externo para CT 102:443
  -> Nginx Proxy Manager no CT 102
  -> http://192.168.3.155:18000
  -> backend AgentEscala no container em 8030
```

Dentro do CT 102, teste o NPM com `https://escala.ks-sm.net` e teste o backend
direto com `http://192.168.3.155:18000`. Não use `:9443` como critério interno,
porque `9443` é externo ao CT.

## Pré-Requisitos

- Docker Engine ativo no CT 102.
- Docker Compose disponível (`docker compose` ou `docker-compose`).
- Nginx Proxy Manager já operacional no CT 102.
- Proxy host NPM para `escala.ks-sm.net` apontando para `192.168.3.155:18000`.
- Roteador/firewall encaminhando `9443` externo para `192.168.3.155:443`.
- Certificado local/custom/self-signed configurado no NPM conforme política do homelab.

## Arquivos Relevantes

- `infra/docker-compose.homelab.yml`: stack do backend + banco com rede e volume dedicados.
- `infra/.env.homelab.example`: template das variáveis do CT 102.
- `infra/scripts/couple_to_homelab.sh`: validação e primeira subida com dry-run.
- `infra/scripts/rebuild_official_homelab.sh`: rebuild canônico da stack oficial já ativa.
- `infra/scripts/backup_postgres.sh`: backup manual do banco do AgentEscala.
- `infra/scripts/restore_postgres.sh`: restore destrutivo com confirmação explícita.
- `infra/scripts/plan_npm_publish.sh`: resumo seguro da configuração NPM esperada.
- `infra/examples/prometheus/agentescala-scrape.yml`: exemplo de scrape Prometheus.

## Variáveis Essenciais

Valores operacionais esperados no CT 102:

```text
COMPOSE_PROJECT_NAME=agentescala_official
AGENTESCALA_IMAGE=agentescala:homelab
PUBLIC_DOMAIN=escala.ks-sm.net
PUBLIC_PORT=9443
PUBLIC_BASE_URL=https://escala.ks-sm.net:9443
VITE_API_BASE_URL=https://escala.ks-sm.net:9443
BACKEND_BIND_ADDRESS=192.168.3.155
BACKEND_HOST_PORT=18000
POSTGRES_VOLUME_NAME=agentescala_postgres_data_official18000
INTERNAL_NETWORK_NAME=agentescala_official_internal
```

`VITE_API_BASE_URL` precisa incluir `:9443`, porque o navegador dos usuários vê
essa origem externa. O NPM, por outro lado, escuta em `443` dentro do CT.

`infra/.env.homelab` ativo precisa manter segredos reais e coerentes com o
volume Postgres persistido do stack oficial. Valores `CHANGE_ME_*` pertencem ao
template `.env.homelab.example`, não ao ambiente de produção local.

## Primeira Subida

```bash
cd /opt/repos/AgentEscala
cp infra/.env.homelab.example infra/.env.homelab
nano infra/.env.homelab

./infra/scripts/couple_to_homelab.sh --dry-run
./infra/scripts/couple_to_homelab.sh --build
```

O script valida variáveis, porta, compose e build. Se o `up` falhar, o rollback
é restrito ao stack do AgentEscala.

## Deploy Canônico Local Em Um Comando

Para execução local no CT 102 com a sequência oficial encapsulada em script:

```bash
cd /opt/repos/AgentEscala
./infra/scripts/deploy_local_canonical.sh
```

Esse script executa na ordem correta:

1. valida que o repositório está limpo e na branch `main`;
2. sincroniza com `origin/main` em modo fast-forward only;
3. chama `./infra/scripts/rebuild_official_homelab.sh`;
4. roda `./infra/scripts/run_homelab_validation.sh` ao final.

Observação operacional:

- o script canônico já lida com `docker compose` plugin ou `docker-compose` v1
  do Debian;
- a validação final no CT 102 testa `https://escala.ks-sm.net` e o backend
  direto em `18000`;
- testes explícitos em `:9443` devem ser feitos apenas de um cliente externo,
  porque essa porta pertence à borda do roteador/firewall.

Exemplos úteis:

```bash
# mantém a sincronização git padrão
./infra/scripts/deploy_local_canonical.sh

# repassa flags para o rebuild oficial
./infra/scripts/deploy_local_canonical.sh -- --allow-dirty

# usa o commit atual sem fetch/merge
./infra/scripts/deploy_local_canonical.sh --skip-git-sync
```

## Atualização De Stack Já Ativo

Quando o stack já está rodando, a porta `18000` estará ocupada pelo próprio
backend oficial. Nesse cenário, o caminho canônico é o script abaixo:

```bash
cd /opt/repos/AgentEscala
git fetch origin main
git merge --ff-only FETCH_HEAD

./infra/scripts/rebuild_official_homelab.sh
```

O script valida que está usando apenas a topologia oficial do CT 102:

```text
COMPOSE_PROJECT_NAME=agentescala_official
AGENTESCALA_IMAGE=agentescala:homelab
BACKEND_BIND_ADDRESS=192.168.3.155
BACKEND_HOST_PORT=18000
POSTGRES_VOLUME_NAME=agentescala_postgres_data_official18000
INTERNAL_NETWORK_NAME=agentescala_official_internal
VITE_API_BASE_URL=https://escala.ks-sm.net:9443
```

Ele também roda `npm run lint`, `npm run test`, executa o build Docker com
`--force-recreate backend`, valida `/health` no backend direto e confirma que o
bundle publicado contém `https://escala.ks-sm.net:9443`.

Se houver uma alteração local ainda não commitada que precisa ser testada antes
do merge, use conscientemente:

```bash
./infra/scripts/rebuild_official_homelab.sh --allow-dirty
```

O prefixo `DEBUG=false` já é aplicado pelo script para evitar que um
`DEBUG=release` exportado no shell do CT seja injetado no container. O backend
espera booleano.

Não use `docker-compose up -d --build` na raiz do repositório para atualizar o
CT 102. Esse comando usa `docker-compose.yml`, cria a stack local `agentescala`
e pode publicar portas/volumes não canônicos. A stack oficial sempre deve ser
atualizada com `infra/docker-compose.homelab.yml` e projeto
`agentescala_official`.

## Nginx Proxy Manager

Configuração esperada do proxy host ativo:

```text
domain=escala.ks-sm.net
scheme=http
forward_host=192.168.3.155
forward_port=18000
enabled=1
ssl_forced=1
hsts_enabled=1
http2_support=1
```

Se houver proxy hosts duplicados para `escala.ks-sm.net`, mantenha apenas um
habilitado. No CT 102 validado, o `id=8` é o ativo e o `id=7` permanece
desativado para rollback/rastreabilidade.

## Validação Pós-Deploy

Status:

```bash
docker-compose -p agentescala_official \
  -f infra/docker-compose.homelab.yml \
  --env-file infra/.env.homelab ps
```

Backend direto:

```bash
curl -fsS http://192.168.3.155:18000/health
curl -fsS http://192.168.3.155:18000/api/v1/info
curl -fsS http://192.168.3.155:18000/metrics | grep agentescala_http_requests_total
```

Via NPM interno:

```bash
curl -kfsS https://escala.ks-sm.net/health
curl -kfsS https://escala.ks-sm.net/api/v1/info
curl -kfsS https://escala.ks-sm.net/login | grep AgentEscala
```

Checklist automatizado no CT 102:

```bash
./infra/scripts/run_homelab_validation.sh
```

Validação da borda externa real, somente fora do CT 102:

```bash
./infra/scripts/run_homelab_validation.sh --check-public-port
```

CORS/login simulando a origem externa real:

```bash
curl -k -X OPTIONS https://escala.ks-sm.net/api/auth/login \
  -H 'Origin: https://escala.ks-sm.net:9443' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type' \
  -D -

curl -k -X POST https://escala.ks-sm.net/api/auth/login \
  -H 'Origin: https://escala.ks-sm.net:9443' \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@agentescala.com","password":"admin"}'
```

Bundle frontend:

```bash
ASSET=$(curl -kfsS https://escala.ks-sm.net/ | grep -o '/assets/index-[^" ]*\.js' | head -1)
curl -kfsS "https://escala.ks-sm.net${ASSET}" | grep 'https://escala.ks-sm.net:9443'
```

## Migrações, Seed E Validação

- Migrações Alembic rodam automaticamente na inicialização do backend.
- Seed deve ser usado apenas em primeira subida, reset planejado ou ambiente de teste.

```bash
docker-compose -p agentescala_official \
  -f infra/docker-compose.homelab.yml \
  --env-file infra/.env.homelab \
  exec backend env \
  AGENTESCALA_SEED_DEFAULT_PASSWORD='CHANGE_ME_RUNTIME' \
  AGENTESCALA_PRIMARY_ADMIN_PASSWORD='CHANGE_ME_RUNTIME' \
  python -m backend.seed
```

## Operação

```bash
docker-compose -p agentescala_official -f infra/docker-compose.homelab.yml --env-file infra/.env.homelab logs -f backend
docker-compose -p agentescala_official -f infra/docker-compose.homelab.yml --env-file infra/.env.homelab restart backend
docker-compose -p agentescala_official -f infra/docker-compose.homelab.yml --env-file infra/.env.homelab ps
```

## Rollback

Rollback do stack oficial:

```bash
docker-compose -p agentescala_official \
  -f infra/docker-compose.homelab.yml \
  --env-file infra/.env.homelab \
  down
```

O volume do banco permanece preservado.

Rollback para stack legado (`/root/AgentEscala`) só deve ser usado em emergência,
com revisão de portas e NPM, porque a arquitetura canônica atual é
`/opt/repos/AgentEscala` + `agentescala_official`.

## Boas Práticas

- Usar senhas fortes e `SECRET_KEY` única.
- Restringir `CORS_ALLOW_ORIGINS` aos hosts realmente usados.
- Fazer backup antes de mexer no NPM.
- Não reutilizar volume ou rede sem intenção explícita.
- Não testar `:9443` de dentro do CT como único critério.
- Não reativar proxy hosts duplicados sem revisar o NPM.
- Não usar `/root/AgentEscala` para novos deploys.

## Validação Automatizada

```bash
./infra/scripts/run_homelab_validation.sh --print-only
./infra/scripts/run_homelab_validation.sh \
  --domain escala.ks-sm.net \
  --public-port 9443 \
  --local-base-url http://192.168.3.155:18000
```

## Verificação De Conflitos Antes Do Merge

```bash
./infra/scripts/check_merge_readiness.sh
```

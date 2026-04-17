# Guia Operacional Do AgentEscala

Este guia resume a operação diária do AgentEscala no CT 102. Ele reflete a
arquitetura canônica validada em abril de 2026.

## Recursos Ativos

- Clone ativo: `/opt/repos/AgentEscala`
- Projeto Compose: `agentescala_official`
- Compose file: `infra/docker-compose.homelab.yml`
- Env file: `infra/.env.homelab`
- Backend no host CT 102: `192.168.3.155:18000`
- Porta interna do backend: `8030`
- Rede Docker: `agentescala_official_internal`
- Volume Postgres: `agentescala_postgres_data_official18000`
- Domínio público: `https://escala.ks-sm.net:9443`

## Regra De Rede

Dentro do CT 102, o Nginx Proxy Manager escuta em `443`. A porta `9443` é
externa ao CT e vem do roteador/firewall:

```text
externo :9443 -> CT 102:443 -> NPM -> 192.168.3.155:18000 -> container:8030
```

Por isso:

- navegador externo usa `https://escala.ks-sm.net:9443`;
- NPM interno é validado por `https://escala.ks-sm.net`;
- backend direto é validado por `http://192.168.3.155:18000`.

## Atualização Segura

```bash
cd /opt/repos/AgentEscala
git fetch origin main
git merge --ff-only FETCH_HEAD

DEBUG=false docker-compose -p agentescala_official \
  -f infra/docker-compose.homelab.yml \
  --env-file infra/.env.homelab \
  up -d --build --force-recreate backend
```

Use `DEBUG=false` para impedir que variáveis exportadas no shell do CT, como
`DEBUG=release`, sejam injetadas no backend.

## Validação Mínima

```bash
docker-compose -p agentescala_official \
  -f infra/docker-compose.homelab.yml \
  --env-file infra/.env.homelab ps

curl -sf http://192.168.3.155:18000/health
curl -kfsS https://escala.ks-sm.net/health
curl -kfsS https://escala.ks-sm.net/api/v1/info
curl -kfsS https://escala.ks-sm.net/metrics | grep agentescala_http_requests_total
```

Validar login e CORS externo:

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

## Logs E Troubleshooting

```bash
docker-compose -p agentescala_official \
  -f infra/docker-compose.homelab.yml \
  --env-file infra/.env.homelab logs -f backend

docker-compose -p agentescala_official \
  -f infra/docker-compose.homelab.yml \
  --env-file infra/.env.homelab ps
```

Inspecionar NPM:

```bash
docker exec npm sqlite3 /data/database.sqlite \
  "select id, domain_names, forward_scheme, forward_host, forward_port, enabled from proxy_host where domain_names like '%escala%';"
```

Esperado:

```text
id=8 enabled=1 forward_host=192.168.3.155 forward_port=18000
id=7 enabled=0 duplicata preservada
```

## Backup

```bash
./infra/scripts/backup_postgres.sh --env-file infra/.env.homelab
```

Antes de alterar NPM:

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
docker exec npm cp /data/database.sqlite /data/database.sqlite.bak_${TS}_manual
docker cp npm:/data/database.sqlite /root/agentescala_backups/npm_database_${TS}.sqlite
```

## Rollback

Rollback do stack oficial:

```bash
docker-compose -p agentescala_official \
  -f infra/docker-compose.homelab.yml \
  --env-file infra/.env.homelab down
```

O volume do banco permanece preservado.

O stack legado em `/root/AgentEscala` está fora da arquitetura ativa. Só usar em
emergência, após revisar portas, volume e NPM.

## Integração Prometheus

Exemplo de job de scrape:

- `infra/examples/prometheus/agentescala-scrape.yml`

O target canônico é:

```text
192.168.3.155:18000
```

## Backup E Restore

- Backup: `infra/scripts/backup_postgres.sh`
- Restore: `infra/scripts/restore_postgres.sh`

Detalhes em `docs/backup_restore.md`.

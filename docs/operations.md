# Guia Operacional do AgentEscala

Este guia resume a operação mínima do AgentEscala no CT 102, com foco em isolamento, rollback e convivência segura com os demais stacks do host.

## Recursos usados pelo AgentEscala
- Projeto Compose: `agentescala`
- Compose file: `infra/docker-compose.homelab.yml`
- Porta local sugerida do backend: `127.0.0.1:18000`
- Rede interna sugerida: `agentescala_internal`
- Volume Postgres sugerido: `agentescala_postgres_data`

## Subida segura
```bash
cd /root/AgentEscala/infra
cp .env.homelab.example .env.homelab
nano .env.homelab
./scripts/couple_to_homelab.sh --dry-run
./scripts/couple_to_homelab.sh --build
```

## Validação mínima após subida
```bash
curl -sf http://127.0.0.1:18000/health
curl -sf http://127.0.0.1:18000/metrics | grep agentescala_http_requests_total
docker-compose -p agentescala -f docker-compose.homelab.yml exec backend python -m backend.seed
docker-compose -p agentescala -f docker-compose.homelab.yml exec backend \
  env AGENTESCALA_BASE_URL=http://127.0.0.1:8000 python -m backend.validate
```

## Logs e troubleshooting
```bash
docker-compose -p agentescala -f infra/docker-compose.homelab.yml logs -f backend
docker-compose -p agentescala -f infra/docker-compose.homelab.yml ps
```

## Rollback do stack do AgentEscala
```bash
docker-compose -p agentescala -f infra/docker-compose.homelab.yml down
```

Esse rollback remove apenas containers e rede do AgentEscala. O volume do banco permanece preservado.

## Publicação via NPM
```bash
./infra/scripts/plan_npm_publish.sh
```

Use o plano gerado para criar manualmente o Proxy Host no NPM sem tocar em hosts existentes.

## Integração Prometheus
Exemplo de job de scrape:
- `infra/examples/prometheus/agentescala-scrape.yml`

## Backup e restore
- Backup: `infra/scripts/backup_postgres.sh`
- Restore: `infra/scripts/restore_postgres.sh`

Os detalhes operacionais estão em `docs/backup_restore.md`.
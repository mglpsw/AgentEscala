# Backup e Restore do AgentEscala

Este guia cobre o fluxo mínimo e auditável de backup e restore do PostgreSQL do AgentEscala.

## Princípios
- atuar apenas sobre o banco do AgentEscala
- não tocar em bancos ou stacks de outros serviços do CT 102
- manter os scripts simples, explícitos e reversíveis
- exigir confirmação explícita para restore destrutivo

## Scripts
- Backup: `infra/scripts/backup_postgres.sh`
- Restore: `infra/scripts/restore_postgres.sh`

## Backup

Exemplo:
```bash
./infra/scripts/backup_postgres.sh --env-file infra/.env.homelab
```

Saída padrão:
- diretório: `infra/backups/YYYYMMDD_HHMMSS/`
- dump: `agentescala.dump`
- metadados: `metadata.env`

Dry-run:
```bash
./infra/scripts/backup_postgres.sh --env-file infra/.env.homelab --dry-run
```

## Restore

Exemplo:
```bash
./infra/scripts/restore_postgres.sh \
  --env-file infra/.env.homelab \
  --dump-file infra/backups/20260413_230000/agentescala.dump \
  --confirm-restore
```

Dry-run:
```bash
./infra/scripts/restore_postgres.sh \
  --env-file infra/.env.homelab \
  --dump-file infra/backups/20260413_230000/agentescala.dump \
  --dry-run
```

## Comportamento do restore
- o container backend do AgentEscala é parado temporariamente
- conexões ao banco do AgentEscala são encerradas
- o banco do AgentEscala é recriado
- o dump é restaurado
- o backend é iniciado novamente

Esse fluxo é destrutivo apenas para os dados atuais do AgentEscala. Nenhum outro stack é afetado.

## Retenção sugerida
- manter ao menos 7 backups diários
- manter 4 backups semanais
- armazenar uma cópia fora do CT 102 se o risco operacional justificar

## Validação pós-restore
```bash
curl -sf http://127.0.0.1:18000/health
docker-compose -p agentescala -f infra/docker-compose.homelab.yml exec backend \
  env AGENTESCALA_BASE_URL=http://127.0.0.1:8000 python -m backend.validate
```
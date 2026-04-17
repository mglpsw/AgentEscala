# Plano De Limpeza CT 102 - AgentEscala

Este plano **não deve ser executado automaticamente**. Ele lista o que pode ser
removido em uma janela futura, considerando que o estado canônico atual é:

- clone ativo: `/opt/repos/AgentEscala`
- stack ativo: `agentescala_official`
- backend ativo: `192.168.3.155:18000->8030`
- NPM interno: `443`
- acesso externo: `https://escala.ks-sm.net:9443` via port-forward do roteador
- volume ativo: `agentescala_postgres_data_official18000`

## Resultado Da Verificação Em 2026-04-17

Diretórios encontrados:

```text
/opt/repos/AgentEscala          manter, fonte canônica
/root/ct102-runbooks            manter, documentação operacional interna do CT
/root/agentescala_backups       manter, backups e evidências de rollback
/root/AgentEscala               legado, candidato a exclusão
/root/AgentEscala.main-clone    legado, candidato a exclusão
/root/AgentEscala.worktrees     legado, candidato a exclusão
```

Tamanhos observados:

```text
/root/AgentEscala             ~583M
/root/AgentEscala.main-clone  ~9.5M
/root/AgentEscala.worktrees   ~374M
/opt/repos/AgentEscala        ~8.9M
/root/agentescala_backups     ~15M
/root/ct102-runbooks          ~12K
```

Containers Docker:

```text
agentescala_official_backend_1   manter, ativo
agentescala_official_db_1        manter, ativo
agentescala_backend_1            legado, parado, candidato a remoção
agentescala_db_1                 legado, parado, candidato a remoção
npm                              manter
```

Volumes Docker:

```text
agentescala_postgres_data_official18000   manter, ativo
agentescala_postgres_data                 legado, candidato a remoção após backup frio
agentescala_postgres_data_local8030       legado, candidato a remoção após backup frio
```

Redes Docker:

```text
agentescala_official_internal   manter, ativa
agentescala_internal            legado, candidato a remoção
infra_default                   legado aparente, candidato a remoção se sem containers
npm_default                     manter
```

NPM:

```text
proxy_host id=8   manter, ativo para escala.ks-sm.net -> 192.168.3.155:18000
proxy_host id=7   duplicata desativada, candidato a exclusão futura
```

Imagens Docker candidatas a limpeza após validação:

```text
agentescala_backend:latest   legado
infra_backend:latest         legado aparente; não há container/compose ativo confiável
```

## Ordem Recomendada

### 1. Congelar evidências

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p /root/agentescala_backups/${TS}_pre_cleanup

docker ps -a > /root/agentescala_backups/${TS}_pre_cleanup/docker_ps.txt
docker volume ls > /root/agentescala_backups/${TS}_pre_cleanup/docker_volumes.txt
docker network ls > /root/agentescala_backups/${TS}_pre_cleanup/docker_networks.txt
ss -ltnp > /root/agentescala_backups/${TS}_pre_cleanup/ss_ltnp.txt
docker exec npm sqlite3 /data/database.sqlite \
  "select id, domain_names, forward_host, forward_port, enabled from proxy_host order by id;" \
  > /root/agentescala_backups/${TS}_pre_cleanup/npm_proxy_hosts.txt
```

### 2. Validar que o canônico segue saudável

```bash
curl -fsS http://192.168.3.155:18000/health
curl -kfsS https://escala.ks-sm.net/health
curl -kfsS https://escala.ks-sm.net/api/v1/info
```

### 3. Criar backup frio dos legados

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p /root/agentescala_backups/${TS}_legacy_dirs
tar czf /root/agentescala_backups/${TS}_legacy_dirs/root_AgentEscala.tgz -C /root AgentEscala
tar czf /root/agentescala_backups/${TS}_legacy_dirs/root_AgentEscala_main_clone.tgz -C /root AgentEscala.main-clone
tar czf /root/agentescala_backups/${TS}_legacy_dirs/root_AgentEscala_worktrees.tgz -C /root AgentEscala.worktrees
```

Volumes legados:

```bash
docker run --rm -v agentescala_postgres_data:/data:ro \
  -v /root/agentescala_backups/${TS}_legacy_dirs:/backup alpine \
  sh -c 'cd /data && tar czf /backup/agentescala_postgres_data.tgz .'

docker run --rm -v agentescala_postgres_data_local8030:/data:ro \
  -v /root/agentescala_backups/${TS}_legacy_dirs:/backup alpine \
  sh -c 'cd /data && tar czf /backup/agentescala_postgres_data_local8030.tgz .'
```

### 4. Remover containers legados

Executar somente após backups e validação:

```bash
docker rm agentescala_backend_1 agentescala_db_1
```

### 5. Remover redes legadas vazias

Validar antes:

```bash
docker network inspect agentescala_internal infra_default
```

Remover se não houver containers:

```bash
docker network rm agentescala_internal infra_default
```

### 6. Remover volumes legados

Executar somente após backup frio e uma janela de observação:

```bash
docker volume rm agentescala_postgres_data agentescala_postgres_data_local8030
```

### 7. Remover diretórios legados

Executar somente após backup frio:

```bash
rm -rf /root/AgentEscala
rm -rf /root/AgentEscala.main-clone
rm -rf /root/AgentEscala.worktrees
```

### 8. Remover proxy host duplicado do NPM

Preferir manter desativado por uma janela. Se for realmente excluir:

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
docker exec npm cp /data/database.sqlite /data/database.sqlite.bak_${TS}_before_delete_proxy_host_7
docker exec npm sqlite3 /data/database.sqlite "delete from proxy_host where id=7 and enabled=0;"
docker exec npm nginx -t
docker exec npm nginx -s reload
```

### 9. Remover imagens legadas

Validar antes:

```bash
docker ps -a --filter ancestor=agentescala_backend:latest
docker ps -a --filter ancestor=infra_backend:latest
```

Remover se sem uso:

```bash
docker rmi agentescala_backend:latest infra_backend:latest
```

## O Que Nao Remover

- `/opt/repos/AgentEscala`
- `/root/ct102-runbooks`
- `/root/agentescala_backups`
- container `npm`
- stack `agentescala_official`
- volume `agentescala_postgres_data_official18000`
- rede `agentescala_official_internal`
- proxy host NPM `id=8`

## Critério De Conclusão

A limpeza só deve ser considerada concluída quando:

- `docker ps -a` mostrar apenas `agentescala_official_*` para AgentEscala;
- `docker volume ls` mostrar apenas `agentescala_postgres_data_official18000`;
- `docker network ls` mostrar apenas `agentescala_official_internal` para AgentEscala;
- NPM tiver um único proxy host ativo para `escala.ks-sm.net`;
- `https://escala.ks-sm.net/health` retornar `200`;
- login com origem `https://escala.ks-sm.net:9443` retornar `200`.

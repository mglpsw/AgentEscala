# Diagnóstico de roteamento NPM/OpenResty — 2026-04-16

## Contexto
Solicitação: validar frontend estável em `:8030`, inspecionar containers `agentescala_frontend` e NPM/OpenResty, e corrigir roteamento para `escala.ks-sm.net:9443` sem criar frontend duplicado.

## Execução no ambiente atual

### 1) Verificação HTTP local do frontend em 8030
Comandos executados:

```bash
curl -sSI http://127.0.0.1:8030/
curl -sSI http://127.0.0.1:8030/login
curl -s http://127.0.0.1:8030/ | head -n 40
curl -s http://127.0.0.1:8030/login | head -n 40
```

Resultado:
- `curl: (7) Failed to connect to 127.0.0.1 port 8030 after 0 ms: Couldn't connect to server`

### 2) Inspeção do container `agentescala_frontend`
Comandos executados:

```bash
docker inspect agentescala_frontend
docker logs --tail=200 agentescala_frontend
docker exec agentescala_frontend sh -c 'nginx -T'
```

Resultado:
- `/bin/bash: line 1: docker: command not found`

### 3) Inspeção NPM/OpenResty
Comandos executados:

```bash
docker ps --format '{{.Names}}' | grep -Ei 'npm|nginx|openresty'
docker exec "$NPM_CONTAINER" sh -c 'nginx -T'
docker exec "$NPM_CONTAINER" sh -c 'find /etc/nginx -maxdepth 4 -type f | sort'
docker exec "$NPM_CONTAINER" sh -c 'grep -R "escala.ks-sm.net" -n /etc/nginx || true'
```

Resultado:
- `/bin/bash: line 1: docker: command not found`

## Conclusão objetiva
No ambiente desta execução não há binário `docker` disponível, portanto **não foi possível**:
- acessar os containers citados;
- extrair `nginx -T` do frontend ou do NPM/OpenResty;
- validar/corrigir roteamento do NPM com evidência técnica local.

## Mudanças aplicadas
Nenhuma alteração de infraestrutura/stack foi realizada.
Nenhum frontend duplicado foi criado.
Nenhum backend foi modificado.

# Guia de Deploy em Homelab

Este guia explica como implantar o AgentEscala no CT 102 como stack Docker isolado, sem alterar serviços existentes do host e sem depender de Traefik.

## Pré-requisitos
- Docker e Docker Compose instalados no host
- Host CT 102 com acesso ao daemon Docker
- Porta local livre para o backend do AgentEScala (ex.: `18000`)
- Domínio `escalas.ks-sm.net` apontando para o proxy reverso/NPM existente na porta `9443`
- Certificado local/custom/self-signed já preparado no NPM, se a publicação externa for habilitada

## Arquivos relevantes
- `infra/docker-compose.homelab.yml`: stack do backend + banco com rede e volume isoláveis por ambiente
- `infra/.env.homelab.example`: template de variáveis de ambiente
- `infra/scripts/couple_to_homelab.sh`: script para validar e subir apenas o stack do AgentEScala
- `infra/scripts/backup_postgres.sh`: backup manual do banco do AgentEScala
- `infra/scripts/restore_postgres.sh`: restore destrutivo com confirmação explícita
- `infra/scripts/plan_npm_publish.sh`: helper para planejar a publicação no NPM
- `infra/examples/prometheus/agentescala-scrape.yml`: exemplo de scrape Prometheus

## Princípios operacionais
- Não editar compose files de outros serviços do CT 102
- Não reiniciar NPM, Nextcloud, OpenWebUI, AIOps ou qualquer outro stack
- Não reaproveitar redes/volumes existentes sem confirmação explícita
- Publicar o AgentEScala por bind local dedicado e proxy reverso manual, não por mudança global no host

## Passo a passo

1. **Preparar variáveis**
```bash
cd infra
cp .env.homelab.example .env.homelab
nano .env.homelab
# Ajuste: POSTGRES_PASSWORD, SECRET_KEY, BACKEND_HOST_PORT, PUBLIC_DOMAIN,
# BACKEND_BIND_ADDRESS, POSTGRES_VOLUME_NAME e INTERNAL_NETWORK_NAME
```

2. **Executar dry-run antes de qualquer deploy**
```bash
./scripts/couple_to_homelab.sh --dry-run
```

3. **Executar script de deploy**
```bash
./scripts/couple_to_homelab.sh --build
```
O script valida variáveis, verifica conflito de porta, valida o compose e sobe apenas o stack do AgentEScala. Se o `up` falhar, o rollback é restrito ao próprio stack do AgentEScala.

4. **Verificar status**
```bash
docker compose -p agentescala -f infra/docker-compose.homelab.yml --env-file infra/.env.homelab ps
```
Containers devem estar `Up` e backend com healthcheck `healthy`.

5. **Validar localmente antes do proxy**
- API local: `http://127.0.0.1:18000`
- Health local: `http://127.0.0.1:18000/health`
- Métricas locais: `http://127.0.0.1:18000/metrics`

## Migrações, seed e validação
- Migrações Alembic rodam automaticamente na inicialização do container backend.
- Para rodar seed:
```bash
docker-compose -p agentescala -f docker-compose.homelab.yml exec backend python -m backend.seed
```

- Para validar o runtime HTTP fim a fim:
```bash
docker-compose -p agentescala -f docker-compose.homelab.yml exec backend \
	env AGENTESCALA_BASE_URL=http://127.0.0.1:18000 python -m backend.validate
```

## Operação
- Logs: `docker-compose -p agentescala -f docker-compose.homelab.yml logs -f backend`
- Reiniciar backend: `docker-compose -p agentescala -f docker-compose.homelab.yml restart backend`
- Atualizar imagem: reexecutar o script com `--build`
- Runbook resumido: `docs/operations.md`
- Backup e restore: `docs/backup_restore.md`

## Publicação segura em `escalas.ks-sm.net:9443`

### Opção recomendada nesta fase
- Suba o AgentEScala no CT 102 com `BACKEND_BIND_ADDRESS` local ou IP interno controlado e `BACKEND_HOST_PORT` dedicado
- No NPM, crie um novo Proxy Host para `escalas.ks-sm.net`
- Use certificado local/custom/self-signed
- Não habilite Force SSL
- Aponte o upstream para `http://IP_DO_CT102:BACKEND_HOST_PORT`

O modelo de proxy reverso foi validado localmente com um container Nginx efêmero apontando para o bind do AgentEScala. O NPM real não foi alterado nesta rodada.

### Observação importante
Se o NPM estiver em container separado, `127.0.0.1` não será acessível como upstream a partir dele. Nesse caso, ajuste `BACKEND_BIND_ADDRESS` para o IP LAN do CT 102 ou `0.0.0.0` após revisar o risco.

### Caminho `/api` para futuro frontend
Nesta rodada o escopo é apenas backend. A publicação mais simples e segura é expor o backend no host inteiro `escalas.ks-sm.net:9443`. Se um frontend separado for adicionado depois, mantenha o mesmo host e crie uma location `/api/` no NPM com rewrite para o backend, sem alterar a aplicação nesta etapa.

### Verdade operacional: fallback SPA

O frontend React é servido pelo backend FastAPI via StaticFiles, com fallback SPA já implementado no handler 404. Não há container nginx servindo o frontend. Se for necessário usar proxy reverso (Nginx, Traefik, NPM), configure fallback SPA no proxy também:

```
location / {
    try_files $uri $uri/ /index.html;
}
```

Se `/login` retornar 404, valide se o build do frontend está presente em `frontend/dist` no container backend.

#### Validação rápida
- `/`, `/login`, `/calendar`, `/swaps` → devem servir index.html
- `/assets/vite.svg` → asset estático
- `/health`, `/metrics` → JSON/texto do backend
- `/users/me` → JSON ou 401

## Boas práticas
- Usar senhas fortes e SECRET_KEY única
- Restringir `CORS_ALLOW_ORIGINS` ao host publicado
- Configurar backups do volume do PostgreSQL
- Não reutilizar volume ou rede sem intenção explícita
- Validar sempre com `--dry-run` antes do deploy real
- Manter a mudança reversível: `docker-compose ... down` deve afetar apenas o stack do AgentEScala


## Validação rápida automatizada

Use o script abaixo para executar (ou apenas imprimir) o checklist de validação de deploy/roteamento:

```bash
./infra/scripts/run_homelab_validation.sh --print-only
./infra/scripts/run_homelab_validation.sh --domain escala.ks-sm.net --public-port 9443 --local-base-url http://127.0.0.1:18000
```

O script cobre baseline de host, saúde local, DNS/TLS externo e inspeção NPM/OpenResty (quando Docker está disponível).


## Verificação de conflitos antes do merge

Antes de abrir/atualizar PR, execute:

```bash
./infra/scripts/check_merge_readiness.sh
```

Esse check falha se existir:
- arquivo em estado de merge pendente (`git ls-files -u`);
- marcador de conflito em arquivo versionado (`<<<<<<<`, `=======`, `>>>>>>>`).

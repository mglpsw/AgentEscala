# Prompt pronto para o Codex — Deploy + Validação no Homelab

Copie e cole o texto abaixo no Codex para ele ajustar o repositório do homelab com segurança e validação guiada.

---

## Prompt

Atue como **Engenheiro DevSecOps Sênior** e execute um ajuste controlado no repositório do homelab do **AgentEscala**.

### Objetivo
Quero que você prepare/ajuste o deploy do AgentEscala no homelab e valide ponta a ponta, **sem quebrar serviços existentes** e **sem recriar componentes já estáveis**.

### Restrições obrigatórias
1. Não alterar stacks não relacionadas (Nextcloud, OpenWebUI, AIOps, etc.).
2. Não subir frontend duplicado se já existir frontend estável publicado.
3. Não trocar backend em produção sem evidência técnica.
4. Não reiniciar NPM globalmente sem necessidade.
5. Executar mudanças mínimas, reversíveis e documentadas.
6. Preservar SSH/liberação administrativa no firewall.

### Contexto esperado
- Deploy com Docker Compose específico do AgentEscala.
- Publicação via Nginx Proxy Manager/OpenResty.
- Domínio público com TLS e roteamento para frontend/backend corretos.

### Plano de execução (ordem obrigatória)

#### 1) Descoberta e baseline
Rode e registre saída resumida:
```bash
pwd
git branch --show-current
git status --short
hostnamectl
ip -br a
ip r
ss -lntp
```

#### 2) Validar artefatos de deploy do repositório
```bash
ls infra
sed -n '1,260p' infra/docker-compose.homelab.yml
sed -n '1,260p' docs/homelab_deploy.md
sed -n '1,260p' infra/scripts/couple_to_homelab.sh
```

Se faltar variável crítica, ajuste `.env.homelab.example` e documentação associada.

#### 3) Hardening de configuração (somente se necessário)
Garanta no deploy:
- `SECRET_KEY` forte e não default.
- `CORS_ALLOW_ORIGINS` explícito para domínio oficial.
- bind de backend controlado (evitar exposição desnecessária).
- healthcheck ativo.
- logs suficientes para troubleshooting.

Se alterar arquivos, explique racional técnico de cada mudança.

#### 4) Dry-run e validações locais
Execute:
```bash
cd infra
./scripts/couple_to_homelab.sh --dry-run
./scripts/couple_to_homelab.sh --build

docker-compose -p agentescala -f docker-compose.homelab.yml ps
docker-compose -p agentescala -f docker-compose.homelab.yml logs --tail=150 backend
```

Depois valide endpoints locais:
```bash
curl -sSI http://127.0.0.1:18000/
curl -sSI http://127.0.0.1:18000/health
curl -sSI http://127.0.0.1:18000/metrics
```

#### 5) Validação de roteamento NPM/OpenResty
Descubra e valide config efetiva:
```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Image}}' | grep -Ei 'npm|nginx|openresty'
NPM_CONTAINER="$(docker ps --format '{{.Names}}' | grep -Ei 'npm|nginx|openresty' | head -n1)"
docker exec "$NPM_CONTAINER" sh -c 'nginx -T' > /tmp/npm_nginx_dump.txt 2>&1

grep -n "server_name" /tmp/npm_nginx_dump.txt | sed -n '1,220p'
grep -n "proxy_pass" /tmp/npm_nginx_dump.txt | sed -n '1,220p'
grep -n "default_server" /tmp/npm_nginx_dump.txt || true
grep -n "escala.ks-sm.net" /tmp/npm_nginx_dump.txt || true
```

Se o domínio cair no default OpenResty:
- corrija **somente** o host de proxy necessário;
- aponte para o alvo estável já existente;
- não subir novo frontend em paralelo;
- não alterar backend se ele já estiver saudável.

#### 6) Validação final externa
```bash
curl -k -sSI https://escala.ks-sm.net:9443/
curl -k -sSI https://escala.ks-sm.net:9443/login
curl -k -s https://escala.ks-sm.net:9443/ | head -n 40
```

Critérios de sucesso:
- domínio não cai mais no default OpenResty;
- frontend esperado abre em `/` e `/login`;
- backend atual preservado;
- sem frontend duplicado.

#### 7) Segurança de webhook Telegram (se houver endpoint)
Propor patch com:
- `X-Telegram-Bot-Api-Secret-Token`;
- token randômico no path;
- allowlist de IP (defesa em profundidade);
- rate limit e idempotência por `update_id`.

#### 8) Entrega final (formato obrigatório)
Responder nesta ordem:
1. mapa do estado atual
2. mudanças aplicadas
3. validação técnica (comandos + resultado)
4. riscos remanescentes
5. rollback rápido
6. resumo executivo

### Regras de edição no repositório
- Preferir alterar somente:
  - `infra/docker-compose.homelab.yml`
  - `infra/.env.homelab.example`
  - `infra/scripts/*.sh`
  - `docs/homelab_deploy.md`
  - docs de operação correlatas
- Não introduzir breaking change sem flag/compatibilidade.
- Se não conseguir validar algo por limitação de ambiente, registrar evidência objetiva do bloqueio.

---

## Referências internas do projeto
- Guia atual: `docs/homelab_deploy.md`
- Stack homelab: `infra/docker-compose.homelab.yml`
- Script de acoplamento/deploy: `infra/scripts/couple_to_homelab.sh`
- Operação: `docs/operations.md`
- Backup/restore: `docs/backup_restore.md`


# Guia de Deploy em Homelab

Este guia explica como implantar o AgentEscala em um ambiente homelab com Docker, Traefik e TLS.

## Pré-requisitos
- Docker e Docker Compose instalados no host
- Rede do Traefik disponível (ex.: `traefik-public`)
- Domínio configurado apontando para o host
- Certificados gerenciados pelo Traefik (Let's Encrypt ou importados)

## Arquivos relevantes
- `infra/docker-compose.homelab.yml`: stack do backend + banco com labels Traefik
- `infra/.env.homelab.example`: template de variáveis de ambiente
- `infra/scripts/couple_to_homelab.sh`: script para acoplar o stack ao homelab

## Passo a passo

1. **Preparar variáveis**
```bash
cd infra
cp .env.homelab.example .env.homelab
nano .env.homelab
# Ajuste: DOMAIN, POSTGRES_PASSWORD, SECRET_KEY, ADMIN_EMAIL, TRAEFIK_NETWORK, certificados
```

2. **Executar script de deploy**
```bash
./scripts/couple_to_homelab.sh --build
```
O script valida variáveis, constrói a imagem e sobe o compose homelab.

3. **Verificar status**
```bash
docker-compose -f docker-compose.homelab.yml ps
```
Containers devem estar `Up` e backend com healthcheck `healthy`.

4. **Acessar**
- API: `https://$DOMAIN`
- Health: `https://$DOMAIN/health`
- Traefik dashboard (se habilitado): `https://traefik.$DOMAIN/dashboard/`

## Migrações e seed
- Migrações Alembic rodam automaticamente na inicialização do container backend.
- Para rodar seed:
```bash
docker-compose -f docker-compose.homelab.yml exec backend python -m backend.seed
```

## Operação
- Logs: `docker-compose -f docker-compose.homelab.yml logs -f backend`
- Reiniciar backend: `docker-compose -f docker-compose.homelab.yml restart backend`
- Atualizar imagem: reexecutar o script com `--build`

## Boas práticas
- Usar senhas fortes e SECRET_KEY única
- Restringir `allow_origins` em produção
- Configurar backups do volume do PostgreSQL
- Habilitar rate limiting no Traefik para exposição pública
- Manter certificados TLS renovados

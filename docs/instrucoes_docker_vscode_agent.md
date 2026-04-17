# Instruções rápidas: Docker + VS Code + Agent

Este guia resume como subir o stack do AgentEscala em Docker, trabalhar no VS Code (Remote Containers/Dev Containers) e quais melhorias priorizar para publicar o stack online.

## Pré-requisitos
- Docker e Docker Compose instalados
- VS Code com a extensão **Dev Containers** (ou **Remote - Containers**)
- Acesso ao repositório AgentEscala
- Porta 5432 e 8000 livres no host (ou ajuste as portas no `docker-compose.yml`)

## Subindo o stack localmente (Docker Compose)
1. Clone o repositório e entre na pasta:
   ```bash
   git clone https://github.com/mglpsw/AgentEscala.git
   cd AgentEscala
   ```
2. Crie o arquivo de ambiente se necessário:
   ```bash
   cp .env.example .env
   # ajuste DATABASE_URL/SECRET_KEY se quiser rodar sem Docker
   ```
3. Suba os serviços:
   ```bash
   docker-compose up -d
   ```
4. Defina as variáveis de senha do seed (`AGENTESCALA_PRIMARY_ADMIN_PASSWORD` e `AGENTESCALA_SEED_DEFAULT_PASSWORD`) com valores fora do Git e aplique o seed:
   ```bash
   docker-compose exec backend python -m backend.seed
   ```
5. Acesse:
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health

## Trabalhando no VS Code com Dev Containers
1. Abra o repositório no VS Code.
2. Instale e habilite a extensão **Dev Containers**.
3. Use `Dev Containers: Attach to Running Container...` e selecione o container `backend` (após o `docker-compose up`).
4. Dentro do container:
   - Dependências já estão instaladas.
   - Rode validação rápida: `python -m compileall backend` ou `python -m backend.validate` (requer banco/seed).
5. Para debugar com um agent (ex.: GitHub Copilot/Codeium), mantenha o workspace aberto normalmente; o Dev Container fornece o ambiente consistente enquanto o agent auxilia na edição de código.

## Publicando o stack online (resumo)
1. Prepare variáveis em `infra/.env.homelab` (ou use `.env` em cloud): `DATABASE_URL`, `SECRET_KEY`, `DOMAIN`, `POSTGRES_PASSWORD`, `ADMIN_EMAIL`.
2. Para homelab com Traefik: `./infra/scripts/couple_to_homelab.sh --build`.
3. Para um VPS/cloud simples: `docker-compose -f docker-compose.yml up -d` (ajuste portas e volumes persistentes).
4. Teste após o deploy:
   ```bash
   curl https://SEU_DOMINIO/health
   curl https://SEU_DOMINIO/shifts
   ```

## Melhorias recomendadas antes de expor publicamente
1. **Aplicar autorização nos endpoints**
   - Usar `require_admin` em rotas administrativas (trocas, usuários) e proteger demais rotas com JWT.
2. **Hardening de segurança**
   - Restringir CORS para domínios confiáveis.
   - Habilitar rate limiting no gateway (Traefik ou Nginx).
   - Rotacionar `SECRET_KEY` e senhas padrão do banco.
3. **Observabilidade**
   - Logging estruturado (JSON) e correlação de requisições.
   - Métricas básicas (requisições, latência, erros) com endpoint dedicado.
4. **Confiabilidade**
   - Backups e retenção do volume do PostgreSQL.
   - Health checks já existem; configure restart_policy no orquestrador.
5. **Automação de validação**
   - Criar suíte mínima de testes (health, auth, exportações, fluxo de trocas).
   - Pipeline CI para rodar testes/linters antes do deploy.

## Diagnóstico rápido
- Logs: `docker-compose logs -f backend`
- Health: `curl http://localhost:8000/health`
- Reset local: `docker-compose down -v && docker-compose up -d && docker-compose exec backend python -m backend.seed`

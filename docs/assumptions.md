# Premissas e Decisões Técnicas

## Objetivo

Documentar as principais premissas, decisões e trade-offs usados no MVP do AgentEscala.

## Premissas de produto
- MVP focado apenas em backend (sem frontend ainda)
- Fluxo de trocas requer aprovação do administrador
- Fuso horário UTC para todos os horários
- Usuários seed exigem senha definida via ambiente (sem credenciais versionadas)

## Arquitetura
- Arquitetura em três camadas (API → Service → Model)
- FastAPI para camada HTTP e validação
- SQLAlchemy ORM com PostgreSQL
- Pydantic para schemas de entrada/saída
- Exportadores dedicados para Excel (openpyxl) e ICS (icalendar)

## Segurança
- Hash de senha com bcrypt via passlib
- Tokens JWT com expiração de 24h; sem refresh token no MVP
- Endpoints sensíveis protegidos com `get_current_user` e `require_admin`
- CORS liberado em dev; restringir em produção
- Sem armazenamento de sessão (stateless)
- Dependências atualizadas para versões com patches de segurança

## Dados e migrações
- Alembic para versionar o schema
- Migração inicial cria users, shifts e swap_requests
- Migrações executadas automaticamente na subida do container
- Seed gera dados realistas para testes rápidos

## Deploy
- Docker Compose para ambiente local
- Compose homelab isolado para CT 102, com bind local configurável, rede dedicada e volume dedicado
- Publicação externa preparada via NPM/manual proxy em `escalas.ks-sm.net:9443`, sem automação destrutiva sobre proxies existentes
- Script `infra/scripts/couple_to_homelab.sh` com `--dry-run`, validação de conflitos e rollback do stack do AgentEscala
- Variáveis de ambiente em `.env.example` e `.env.homelab.example`

## Operação
- Endpoint `/health` para verificação básica
- Logs de requisição em STDOUT
- Endpoint `/metrics` para métricas Prometheus básicas
- Validação manual via `backend/validate.py`

## Limitações conhecidas
- Autorização ainda é mínima; faltam refresh token e regras mais refinadas
- Suíte de testes ainda é enxuta
- Sem rate limiting, refresh token ou recuperação de senha
- Sem frontend ou notificações por e-mail

## Próximos passos recomendados
1. Aplicar dependências de autorização nos endpoints críticos
2. Criar suíte mínima de testes (health, auth, exports, trocas)
3. Adicionar logging estruturado e métricas básicas
4. Endurecer configuração para nuvem pública (TLS gerenciado, rate limiting)

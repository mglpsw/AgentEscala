# Premissas e Decisões Técnicas

## Objetivo

Documentar as principais premissas, decisões e trade-offs usados no MVP do AgentEscala.

## Premissas de produto
- MVP focado apenas em backend (sem frontend ainda)
- Fluxo de trocas requer aprovação do administrador
- Fuso horário UTC para todos os horários
- Usuários seed usam senha padrão `password123`

## Arquitetura
- Arquitetura em três camadas (API → Service → Model)
- FastAPI para camada HTTP e validação
- SQLAlchemy ORM com PostgreSQL
- Pydantic para schemas de entrada/saída
- Exportadores dedicados para Excel (openpyxl) e ICS (icalendar)

## Segurança
- Hash de senha com bcrypt via passlib
- Tokens JWT com expiração de 24h; sem refresh token no MVP
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
- Compose homelab com Traefik, SSL/TLS e rede isolada
- Script `infra/scripts/couple_to_homelab.sh` para acoplar ao homelab
- Variáveis de ambiente em `.env.example` e `.env.homelab.example`

## Operação
- Endpoint `/health` para verificação básica
- Logs via Uvicorn em STDOUT
- Validação manual via `backend/validate.py`

## Limitações conhecidas
- Endpoints ainda não protegidos por papel (auth aplicada só no login)
- Sem suíte de testes automatizados
- Sem rate limiting, refresh token ou recuperação de senha
- Sem frontend ou notificações por e-mail

## Próximos passos recomendados
1. Aplicar dependências de autorização nos endpoints críticos
2. Criar suíte mínima de testes (health, auth, exports, trocas)
3. Adicionar logging estruturado e métricas básicas
4. Endurecer configuração para nuvem pública (TLS gerenciado, rate limiting)

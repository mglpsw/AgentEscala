# Status do Projeto

**Última atualização**: 2026-04-13

## Visão geral

AgentEscala é um sistema de gestão e troca de turnos que permite às equipes administrar escalas com um fluxo de aprovação obrigatória por administrador.

## Status atual: Backend do MVP rodando (aplicação de auth + testes pendentes) ⚠️

O backend roda fim a fim com migrações automáticas, seed, exportações e fluxo de trocas. Endpoints de autenticação existem, mas a aplicação de papéis e a suíte de testes ainda estão pendentes.

### Última validação (2026-04-13)
- Build/up do docker-compose aplica migrações Alembic automaticamente e inicia com sucesso
- Script de seed conclui (6 usuários, 90 turnos, 3 trocas)
- Script de validação passa (health, consultas, exports, validação de trocas)
- Listagem e exportação de trocas retornam todas as solicitações (não apenas pendentes)

## Funcionalidades implementadas

### ✅ Backend principal (100%)
- [x] Estrutura FastAPI
- [x] Modelos de banco (User, Shift, SwapRequest)
- [x] SQLAlchemy com PostgreSQL
- [x] Camada de serviços (regras de negócio)
- [x] Endpoints REST
- [x] Endpoint de health check
- [x] Middleware de CORS
- [x] Configuração por ambiente

### ✅ Gestão de Usuários (100%)
- [x] Modelo de usuário com papéis (Admin, Agent)
- [x] CRUD de usuários
- [x] Camada de serviço de usuário
- [x] Endpoints de gestão de usuários
- [x] Estados ativo/inativo

### ✅ Gestão de Turnos (100%)
- [x] Modelo de turno com informações de agenda
- [x] CRUD de turnos
- [x] Camada de serviço de turnos
- [x] Endpoints de turnos
- [x] Consulta por agente
- [x] Validação de turnos

### ✅ Fluxo de Trocas (100%)
- [x] Modelo SwapRequest com rastreamento de status
- [x] Criação de trocas com validação
- [x] Fluxo de aprovação do admin
- [x] Fluxo de rejeição do admin
- [x] Cancelamento pelo solicitante
- [x] Troca automática dos turnos na aprovação
- [x] Status (pending, approved, rejected, cancelled)
- [x] Registro de motivo e notas do admin

### ✅ Exportações (100%)
- [x] Exportador Excel com formatação profissional
- [x] Exportação para turnos
- [x] Exportação para solicitações de troca
- [x] Abas de metadados
- [x] Exportador ICS (iCalendar)
- [x] Exportação ICS de turnos (individual e em lote)
- [x] Suporte à integração com calendários

### 🟡 Autenticação (parcial)
- [x] Hash de senha e endpoint de login com JWT
- [x] Modelo de usuário usa hashed_password
- [ ] Proteção de endpoints com checagem de papéis
- [ ] Refresh/revogação de token

### ✅ Ambiente de desenvolvimento (100%)
- [x] Dockerfile para containerização
- [x] docker-compose.yml para uso local
- [x] Container PostgreSQL
- [x] Configuração de ambiente (.env.example)
- [x] Script de seed
- [x] Migrações Alembic executadas automaticamente na subida do container
- [x] Setup pronto para dev

### ✅ Implantação homelab (100%)
- [x] docker-compose específico de homelab
- [x] Labels de integração com Traefik
- [x] Configuração SSL/TLS
- [x] Configuração de health check
- [x] Configuração de ambiente (.env.homelab.example)
- [x] Script de deploy (couple_to_homelab.sh)
- [x] Isolamento de rede
- [x] Migrações Alembic rodando antes de iniciar o app

### ✅ Documentação (100%)
- [x] README abrangente
- [x] Guia rápido (QUICKSTART.md)
- [x] Status do projeto (este arquivo)
- [x] Documentação de arquitetura
- [x] Guia de deploy homelab
- [x] Documentação de premissas e decisões
- [x] Documentação da API (gerada pelo FastAPI)

## Status de validação funcional

### ✅ Pode ser validado imediatamente
- [x] Backend inicia com Docker Compose
- [x] Banco inicia e conecta
- [x] Endpoint de health responde
- [x] Documentação da API acessível em /docs
- [x] Seed do banco funciona
- [x] CRUD básico funciona
- [x] Exportação Excel gera arquivos válidos
- [x] Exportação ICS gera arquivos válidos
- [x] Fluxo de trocas com aprovação funciona

### 🟡 Requer ambiente homelab
- [ ] Integração Traefik (requer homelab)
- [ ] Certificados SSL/TLS (requer homelab)
- [ ] Persistência de banco em produção (requer homelab)
- [ ] E2E completo em produção

## Ainda não implementado

### Frontend (futuro)
- [ ] Web UI for agents
- [ ] Web UI for admins
- [ ] Dashboard with statistics
- [ ] Calendar view

### Telegram Bot (Future)
- [ ] Telegram bot integration
- [ ] Shift notifications
- [ ] Swap request notifications
- [ ] Bot commands for common operations

### Authentication & Authorization (Remaining)
- [ ] Protect existing endpoints with JWT and role checks
- [ ] Session management / token refresh
- [ ] Password management (reset/rotation)
- [ ] Admin/agent authorization rules enforced end-to-end

### Advanced Features (Future)
- [ ] Email notifications
- [ ] Recurring shifts
- [ ] Shift templates
- [ ] Reports and analytics
- [ ] Audit logging
- [ ] Multi-timezone support
- [ ] Mobile app

### DevOps (Future)
- [ ] CI/CD pipeline
- [ ] Automated tests
- [ ] Container registry automation
- [ ] Monitoring and observability integration
- [ ] Backup automation

## Technical Debt

- Automated test coverage is absent
- Authentication exists but endpoints are still public
- API error handling is basic and lacks structured logging

## Next Sprint Priorities

1. **Authentication & Authorization**
   - Enforce JWT authentication on critical endpoints
   - Add logout/refresh/token expiry handling
   - Enforce role-based access control

2. **Testing**
   - Unit tests for services
   - Integration tests for API
   - End-to-end tests

3. **Frontend Development**
   - Basic web UI for agents
   - Admin dashboard
   - Calendar view

4. **Notifications**
   - Email notifications for swap requests
   - Email notifications for approvals/rejections

## Known Limitations

1. **Authentication not enforced**: Login works and issues JWTs, but most endpoints still accept user_id/admin_id parameters instead of requiring tokens.
2. **No Frontend**: This is a backend-only MVP. UI will be developed in future sprints.
3. **Basic Validation**: Input validation is basic. More comprehensive validation can be added.
4. **No Audit Trail**: Changes are tracked via updated_at timestamps but full audit logging is not implemented.
5. **Single Timezone**: Currently assumes UTC. Multi-timezone support planned for future.

## Deployment Readiness

### Local Development: ✅ Ready
- Complete docker-compose setup
- Easy one-command startup
- Sample data seeding
- Full functionality available

### Homelab Production: ✅ Ready
- Deployment script available
- Traefik configuration ready
- Labels SSL/TLS configuradas
- Health checks configurados
- Pronto para deploy imediato em homelab

### Nuvem pública: 🟡 Requer trabalho
- Necessita aplicar autenticação primeiro
- Necessita rate limiting
- Necessita hardening adicional de segurança

## Decisões de arquitetura

Veja [docs/assumptions.md](docs/assumptions.md) para decisões técnicas detalhadas e racional.

## Organização do repositório

- **Main Branch**: releases estáveis
- **Development**: desenvolvimento ativo
- **Feature Branches**: features individuais
- **Sem mistura**: código do AgentEscala fica no repositório AgentEscala
- **Homelab separado**: infraestrutura homelab em repositório próprio

## Conclusão

O backend do MVP está **operacional e validado** (migrações, seed, script de validação, exports, fluxo de trocas). Faltam aplicar autenticação nos endpoints e automatizar testes. O sistema pode ser:
- Executado localmente com Docker Compose (Alembic roda automaticamente)
- Seedado com dados de exemplo
- Testado via API/script de validação
- Implantado em homelab (pronto para Traefik)

Os próximos passos devem focar em proteger endpoints com JWT/papéis e adicionar cobertura de testes antes de uma implantação mais ampla.

# Status do Projeto

**Última atualização**: 2026-04-14

## Visão geral

AgentEscala é um sistema de gestão e troca de turnos que permite às equipes administrar escalas com um fluxo de aprovação obrigatória por administrador. Inclui importação estruturada de escala anterior via arquivo tabular.

## Status atual: Importação de escala base implementada e validada em runtime real no CT 102 ✅

O backend roda fim a fim com migrações automáticas, seed, exportações, fluxo de trocas, auth JWT mínima, métricas simples, backup/restore básicos e — nesta rodada — importação estruturada de escala anterior via CSV/XLSX com staging, normalização, validações de consistência e confirmação controlada.

### Última validação (2026-04-14)
- **29 testes** passando (25 novos de importação + 4 de regressão)
- Runtime real validado no CT 102: stack subiu, migração `b3f1a2e4c8d0` rodou, importação e confirmação validadas via HTTP
- Turnos noturnos (virada de dia), exceções reais e detecção de sobreposição funcionando corretamente
- Relatório de inconsistências exportável via CSV
- Rotas existentes (health, metrics, shifts, exports, swaps) intactas após a adição

## Funcionalidades implementadas

### ✅ Importação de Escala Base (100%)
- [x] Modelos de staging: ScheduleImport + ScheduleImportRow
- [x] Migração Alembic para as novas tabelas
- [x] Importação CSV (separadores , e ;) e XLSX via openpyxl
- [x] Mapeamento flexível de colunas com aliases PT-BR e EN
- [x] Normalização de turnos: padrões 08-20, 20-08 (overnight), 10-22
- [x] Suporte a exceções reais: 11-22, 10-17:30, 13:30-22, etc.
- [x] Detecção automática de virada de dia (end <= start)
- [x] Matching de profissional por nome (exato e parcial, case-insensitive)
- [x] Validações de consistência: data obrigatória, horas obrigatórias, duração coerente
- [x] Detecção de duplicatas e sobreposições intra-lote
- [x] Detecção de sobreposição com turnos existentes no DB (ao confirmar)
- [x] Distinção entre erros fatais (INVALID) e não-fatais (WARNING)
- [x] Endpoint de confirmação: staging → Shifts reais, idempotente (409 na segunda confirmação)
- [x] Exportação de relatório de inconsistências em CSV
- [x] Todos os endpoints protegidos com require_admin
- [x] 25 testes automatizados cobrindo parsing, normalização e API

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

### ✅ Autenticação (mínimo operacional)
- [x] Hash de senha e endpoint de login com JWT
- [x] Modelo de usuário usa hashed_password
- [x] Proteção de endpoints sensíveis com JWT e checagem de papéis
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
- [x] Isolamento de rede e volume configurável por ambiente
- [x] Bind local do backend configurável para integração segura com NPM
- [x] Dry-run do script de deploy
- [x] Backup/restore básico do PostgreSQL
- [x] Exemplo de scrape Prometheus do lado do projeto
- [x] Configuração de health check
- [x] Configuração de ambiente (.env.homelab.example)
- [x] Script de deploy (couple_to_homelab.sh)
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
- [x] Endpoints sensíveis exigem JWT/papel correto
- [x] Métricas simples expostas em /metrics
- [x] Testes mínimos automatizados passam (29 testes: 25 de importação + 4 de regressão)
- [x] Backup e restore mínimo do banco podem ser executados
- [x] Modelo de reverse proxy validado localmente sem alterar o NPM
- [x] Importação de escala base via CSV/XLSX validada em runtime real

### 🟡 Requer ambiente homelab
- [ ] Publicação final no NPM com certificado local/custom
- [ ] Validação do host público `escalas.ks-sm.net:9443`
- [ ] Automação externa de retenção/rotação de backups

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
- [ ] Session management / token refresh
- [ ] Password management (reset/rotation)
- [ ] Regras adicionais de autorização refinadas por domínio de negócio

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
- [x] Testes mínimos automatizados
- [ ] Cobertura expandida de testes
- [ ] Container registry automation
- [ ] Monitoring and observability integration
- [ ] Backup automation

## Technical Debt

- Cobertura de testes ainda é intencionalmente enxuta
- Ainda faltam refresh token e regras mais granulares de autorização
- Eventos de startup usam `on_event` e podem migrar para lifespan futuramente

## Next Sprint Priorities

1. **Authentication & Authorization**
   - Add logout/refresh/token expiry handling
   - Refinar regras por recurso (ex.: autoatendimento vs administração)

2. **Testing**
   - Expandir testes de serviço
   - Expandir integração HTTP
   - Adicionar validação de deploy em pipeline

3. **Frontend Development**
   - Basic web UI for agents
   - Admin dashboard
   - Calendar view

4. **Notifications**
   - Email notifications for swap requests
   - Email notifications for approvals/rejections

## Known Limitations

1. **Auth mínima, não completa**: endpoints sensíveis já exigem JWT, mas refresh token/logout e políticas mais finas ainda não existem.
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
- Stack isolado e seguro no CT 102
- Publicação via NPM preparada de forma manual e reversível
- Health checks configurados
- Runtime real já validado no host alvo sem impactar outros serviços

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

O backend do MVP está **operacional, endurecido e validado em runtime real** (migrações, seed, script de validação HTTP, exports, fluxo de trocas, auth mínima, métricas e testes). O sistema pode ser:
- Executado localmente com Docker Compose (Alembic roda automaticamente)
- Seedado com dados de exemplo
- Testado via `pytest` e `backend.validate`
- Implantado em homelab no CT 102 como stack isolado

Os próximos passos devem focar em refinar autorização, ampliar cobertura de testes e publicar o host final no NPM com certificado local/custom, sem expandir escopo além do backend nesta etapa.

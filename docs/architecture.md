# Arquitetura do AgentEscala

## Visão geral

AgentEscala é um sistema de gestão e troca de turnos construído com uma arquitetura moderna e escalável. Este documento descreve a estrutura técnica, os componentes e as decisões principais.

Na validação mais recente, o backend foi executado em runtime real no CT 102 como stack Docker isolado, sem reutilizar serviços de outros projetos e sem alteração destrutiva na infraestrutura existente.

## Arquitetura do sistema

```
┌─────────────────────────────────────────────────────────────┐
│                         Camada de Cliente                    │
│   (Futuro: Web UI, App Mobile, Bot Telegram)                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ HTTP/REST
                            │
┌───────────────────────────┴─────────────────────────────────┐
│                     Camada de API (FastAPI)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  Users   │  │  Shifts  │  │  Swaps   │                  │
│  │ Router   │  │ Router   │  │ Router   │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└───────┼─────────────┼─────────────┼────────────────────────┘
        │             │             │
┌───────┴─────────────┴─────────────┴────────────────────────┐
│                      Camada de Serviço                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  User    │  │  Shift   │  │  Swap    │                  │
│  │ Service  │  │ Service  │  │ Service  │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└───────┼─────────────┼─────────────┼────────────────────────┘
        │             │             │
┌───────┴─────────────┴─────────────┴────────────────────────┐
│                  Camada de Dados (SQLAlchemy)              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │   User   │  │  Shift   │  │  Swap    │                  │
│  │  Model   │  │  Model   │  │ Request  │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└───────┼─────────────┼─────────────┼────────────────────────┘
        │             │             │
        └─────────────┴─────────────┘
                      │
              ┌───────┴────────┐
              │   PostgreSQL   │
              └────────────────┘
```

## Descrição das camadas

### Camada de API
- **Tecnologia**: FastAPI
- **Responsabilidade**: tratar requisições/respostas HTTP, validação e roteamento
- **Componentes**: routers (users, shifts, swaps), esquemas Pydantic, injeção de dependências de DB, tratamento de exceções

### Camada de Serviço
- **Tecnologia**: classes Python
- **Responsabilidade**: regras de negócio, validação e orquestração
- **Componentes**: UserService (usuários), ShiftService (turnos), SwapService (fluxo de trocas)
- **Motivo da separação**: reutilizável entre interfaces e testável isoladamente

### Camada de Dados
- **Tecnologia**: SQLAlchemy ORM
- **Responsabilidade**: persistência, relacionamentos e constraints
- **Componentes**: modelos User, Shift e SwapRequest

### Banco de dados
- **Tecnologia**: PostgreSQL 15
- **Motivação**: ACID, robustez e modelo relacional adequado para escalas/turnos

## Modelo de dados

### Diagrama ER

```
┌────────────────┐
│     User       │
├────────────────┤
│ id (PK)        │
│ email          │
│ name           │
│ role           │◄───────┐
│ is_active      │        │
│ created_at     │        │
│ updated_at     │        │
└────────┬───────┘        │
         │                │
         │ 1:N            │ N:1
         │                │
         ▼                │
┌────────────────┐        │
│     Shift      │        │
├────────────────┤        │
│ id (PK)        │        │
│ agent_id (FK)  │────────┘
│ start_time     │
│ end_time       │        ┌────────────┐
│ title          │        │ SwapRequest│
│ description    │◄───┐   ├────────────┤
│ location       │    │   │ id (PK)    │
│ created_at     │    │   │ requester_id (FK) ───┐
│ updated_at     │    │   │ target_agent_id (FK) ─┼──► User
└────────────────┘    │   │ origin_shift_id (FK) ─┤
                      ├───┤ target_shift_id (FK) ─┘
                      │   │ status/reason/admin_notes
                      │   │ reviewed_by            │
                      │   │ timestamps             │
                      └───┴────────────────────────┘
```

### Entidades principais
- **User**: e-mail único, nome, papel (admin/agent), estado ativo, timestamps
- **Shift**: agente, início/fim, título, descrição, local, timestamps
- **SwapRequest**: solicitante, agente alvo, turno origem/destino, status (pending/approved/rejected/cancelled), motivo, notas do admin, reviewed_by

## Fluxos principais

### CRUD de turnos
1. API recebe requisição, valida schema e abre sessão DB
2. ShiftService cria/atualiza/exclui após validações básicas
3. Resposta retorna modelo serializado

### Fluxo de trocas
1. Solicitante envia turnos de origem/destino e agente alvo
2. Validação garante que os turnos existem e pertencem aos agentes informados
3. Admin aprova/rejeita; na aprovação os agent_ids são trocados
4. Status e reviewed_by são atualizados

### Exportação
- **Excel**: openpyxl, cabeçalhos com metadados, inclui dados do agente e duração
- **ICS**: icalendar, eventos com título/descrição/local, identifica agente na descrição

## Autenticação e segurança
- Login JWT (`/auth/login`) com hash de senha via bcrypt (passlib)
- Dependências FastAPI para extrair e validar token: `get_current_user`, `require_admin`
- Status atual: endpoints sensíveis já exigem JWT e papel adequado; refresh token/logout ainda não implementados
- CORS liberado para dev; ajustar origens em produção

## Migrações e dados
- Alembic configurado em `backend/alembic/`
- Migração inicial cria tabelas users, shifts, swap_requests
- Migrações executam automaticamente na subida do container (compose local/homelab)
- Script `backend/seed.py` cria 1 admin, 5 agentes, 90 turnos e 3 trocas de exemplo
- Script `backend/validate.py` realiza checagens de conectividade, consultas, exportações e validação do fluxo de trocas

## Infraestrutura e deploy
- **Dockerfile**: imagem do backend
- **docker-compose.yml**: ambiente local com PostgreSQL + backend, portas configuráveis para host compartilhado, health checks e migrações automáticas
- **infra/docker-compose.homelab.yml**: stack isolado para CT 102, com bind local configurável, rede interna dedicada e volume dedicado
- **infra/scripts/couple_to_homelab.sh**: script de deploy homelab com dry-run, validação de porta e rollback do stack do AgentEscala
- Variáveis de ambiente em `.env.example` e `.env.homelab.example`

## Operação e observabilidade
- Logs: requisições HTTP registradas em STDOUT com método, path, status e latência
- Saúde: endpoint `/health`
- Métricas: endpoint `/metrics` com contadores e histogramas Prometheus básicos
- Integração futura: scraping pelo stack de monitoramento do CT 200, sem nova stack local no CT 102

## Escalabilidade e futuras melhorias
- Stateless no backend; pode ser replicado horizontalmente com DB compartilhado
- Necessário endurecimento adicional para nuvem pública: rate limiting, rotação de segredos, TLS gerenciado
- Roadmap imediato: refinar autorização, ampliar testes automatizados e endurecer a publicação final via NPM


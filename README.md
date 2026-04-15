# AgentEscala

**AgentEscala** é um sistema profissional de gestão e troca de turnos criado para equipes que precisam organizar escalas de trabalho e administrar solicitações de troca com eficiência.

## Funcionalidades

- **Gestão de Turnos**: criar, atualizar e gerenciar turnos de trabalho para agentes
- **Importação de Escala Base**: importar escala do mês anterior via CSV ou XLSX com normalização e validação automáticas
- **Fluxo de Trocas**: solicitar, listar e cancelar trocas de turnos via interface web (/swaps), com aprovação obrigatória do administrador
## Frontend

O frontend React (Vite + Tailwind) inclui:
- Login protegido por JWT
- Página de calendário de turnos (/calendar)
- Página de trocas (/swaps):
   - Lista trocas reais do usuário logado
   - Permite criar nova solicitação de troca
   - Permite cancelar solicitações pendentes
   - Estados de loading, erro e vazio

Veja instruções detalhadas em [frontend/README.md](frontend/README.md).
- **Exportação para Excel**: planilhas profissionais com formatação e metadados
- **Exportação para ICS**: exportação iCalendar simples para integração com calendários
- **API REST**: API RESTful completa construída com FastAPI
- **Acesso por Papéis**: JWT aplicado nos endpoints sensíveis, com aprovação admin protegida
- **Observabilidade mínima**: healthcheck confiável, logs de requisição e endpoint `/metrics`

## Guia Rápido

### Pré-requisitos

- Docker e Docker Compose
- Git

### Desenvolvimento local

1. Clone o repositório:
```bash
git clone https://github.com/mglpsw/AgentEscala.git
cd AgentEscala
```

2. Suba a aplicação:
```bash
docker-compose up -d
```

Em um host Docker compartilhado, prefira portas isoladas:
```bash
AGENTESCALA_BACKEND_HOST_PORT=18000 AGENTESCALA_DB_HOST_PORT=15432 docker-compose up -d
```

As migrações do banco são aplicadas automaticamente antes de o backend iniciar.

3. Popule o banco com dados de exemplo (senha padrão: `password123`):
```bash
docker-compose exec backend python -m backend.seed
```

4. Acesse a aplicação:
   - API: http://localhost:8000
   - Documentação da API: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health
   - Métricas: http://localhost:8000/metrics

Consulte [QUICKSTART.md](QUICKSTART.md) para instruções detalhadas.

## Arquitetura

AgentEscala é construído com:

- **Backend**: FastAPI (Python 3.11)
- **Banco de Dados**: PostgreSQL 15
- **ORM**: SQLAlchemy
- **Exportação**: openpyxl (Excel), icalendar (ICS)

### Estrutura do projeto

```
AgentEscala/
├── backend/
│   ├── api/           # Endpoints REST
│   ├── config/        # Configuração e banco de dados
│   ├── models/        # Modelos SQLAlchemy
│   ├── services/      # Regras de negócio
│   ├── utils/         # Exportadores e utilidades
│   ├── main.py        # Aplicação FastAPI
│   └── seed.py        # Seed do banco
├── docs/              # Documentação
├── infra/             # Implantação homelab
│   ├── scripts/       # Scripts de deploy
│   └── docker-compose.homelab.yml
├── docker-compose.yml # Ambiente local
└── Dockerfile         # Imagem do container
```

## Funcionalidades principais

### Gestão de turnos

- Criação de turnos com horário de início/fim, título, descrição e local
- Atribuição de turnos a agentes específicos
- Atualização e exclusão de turnos
- Consulta por agente ou intervalo de datas
- Exportação de turnos para Excel ou ICS

### Fluxo de trocas

1. **Solicitação**: o agente inicia a troca informando turnos de origem e destino
2. **Pendente**: a solicitação aguarda revisão do admin
3. **Revisão do Admin**: administrador aprova ou rejeita com observações
4. **Execução**: ao aprovar, os turnos são trocados automaticamente
5. **Rastreamento**: todo histórico fica registrado

### Exportações

**Excel**:
- Formatação profissional com cabeçalhos
- Informações do agente incluídas
- Cálculo de duração
- Aba de metadados
- Disponível para turnos e solicitações de troca

**ICS**:
- Formato iCalendar padrão
- Exportação individual ou em lote
- Compatível com Google Calendar, Outlook etc.
- Inclui informações do agente na descrição

## Endpoints da API

### Usuários
- `POST /users/` - Criar usuário (admin)
- `GET /users/` - Listar usuários (admin)
- `GET /users/agents` - Listar agentes (autenticado)
- `GET /users/admins` - Listar administradores (admin)
- `GET /users/{id}` - Detalhar usuário (admin ou próprio usuário)

### Turnos
- `POST /shifts/` - Criar turno (admin)
- `GET /shifts/` - Listar turnos (autenticado)
- `GET /shifts/agent/{id}` - Listar turnos de um agente (autenticado)
- `GET /shifts/export/excel` - Exportar para Excel (autenticado)
- `GET /shifts/export/ics` - Exportar para ICS (autenticado)
- `GET /shifts/{id}` - Detalhar turno (autenticado)
- `PATCH /shifts/{id}` - Atualizar turno (admin)
- `DELETE /shifts/{id}` - Excluir turno (admin)
- `GET /shifts/{id}/export/ics` - Exportar turno individual para ICS (autenticado)

### Trocas
- `POST /swaps/` - Criar solicitação de troca (usuário autenticado)
- `GET /swaps/` - Listar trocas do usuário autenticado ou todas (admin)
- `GET /swaps/pending` - Listar trocas pendentes (admin)
- `GET /swaps/agent/{id}` - Listar trocas de um agente (admin ou próprio agente)
- `GET /swaps/export/excel` - Exportar para Excel (admin)
- `GET /swaps/{id}` - Detalhar troca (admin ou participantes)
- `POST /swaps/{id}/approve` - Aprovar troca (admin)
- `POST /swaps/{id}/reject` - Rejeitar troca (admin)
- `POST /swaps/{id}/cancel` - Cancelar troca (solicitante autenticado)

### Importação de Escala Base (admin)
- `POST /schedule-imports/` - Upload de arquivo CSV ou XLSX e processamento em staging
- `GET /schedule-imports/` - Listar lotes de importação
- `GET /schedule-imports/{id}` - Detalhe do lote com todas as linhas
- `GET /schedule-imports/{id}/summary` - Resumo de contadores (válidas, alertas, inválidas, duplicatas)
- `GET /schedule-imports/{id}/rows` - Listar linhas; filtrar por `?row_status=invalid|warning|valid`
- `POST /schedule-imports/{id}/confirm` - Confirmar importação: converter linhas válidas em Shifts reais
- `GET /schedule-imports/{id}/report` - Baixar CSV com inconsistências detectadas

**Formato aceito no arquivo de importação:**

| Campo | Obrigatório | Aliases aceitos |
|-------|-------------|-----------------|
| profissional | ✅ | professional, nome, agente |
| data | ✅ | date, data_turno, shift_date |
| hora_inicio | ✅ | start_time, inicio, start_hour |
| hora_fim | ✅ | end_time, fim, end_hour |
| total_horas | ❌ | horas, hours, duration |
| observacoes | ❌ | obs, notes, observations |
| origem | ❌ | source, fonte |
| dia_semana | ❌ | ignorado, aceito para compatibilidade |

Formatos de data aceitos: `DD/MM/YYYY`, `YYYY-MM-DD`, `DD-MM-YYYY`
Formatos de hora aceitos: `HH:MM`, `HH:MM:SS`
Separadores CSV aceitos: `,` e `;`

### Autenticação e observabilidade
- `POST /auth/login` - Obter JWT
- `GET /auth/me` - Obter usuário autenticado
- `GET /health` - Verificação de saúde
- `GET /metrics` - Métricas Prometheus básicas

## Implantação

### Desenvolvimento local
```bash
docker-compose up -d
```

### Implantação em homelab

1. Copie e configure o ambiente:
```bash
cp infra/.env.homelab.example infra/.env.homelab
# Edite infra/.env.homelab com seus valores
```

2. Execute o script de deploy:
```bash
./infra/scripts/couple_to_homelab.sh --dry-run
./infra/scripts/couple_to_homelab.sh --build
```

Veja [docs/homelab_deploy.md](docs/homelab_deploy.md) para instruções detalhadas.

### Runtime validado no CT 102

O backend foi validado em runtime real no CT 102 como stack isolado, sem tocar em serviços existentes, usando projeto Compose dedicado, rede interna dedicada, volume Postgres dedicado, bind local em `127.0.0.1:18000`, seed, validação HTTP end-to-end, backup/restore do PostgreSQL e smoke local do modelo de reverse proxy.

## Desenvolvimento

### Rodando sem Docker
```bash
# Instale dependências
pip install -r backend/requirements.txt

# Defina variáveis de ambiente
export DATABASE_URL="postgresql://user:password@localhost:5432/agentescala"

# Inicie a aplicação
uvicorn backend.main:app --reload
```

### Migrações de banco

As migrações do Alembic rodam automaticamente quando o container inicia (ver docker-compose). Você também pode executá-las manualmente:

```bash
cd backend
alembic upgrade head
```

## Status Atual

O site está acessível sem erros de certificado; o login funciona e a página de calendário carrega corretamente. É possível aceitar solicitações de troca (aprovar/rejeitar). No entanto, há limitações operacionais atuais:

- Não é possível criar ou gerenciar usuários via interface.
- Não é possível alterar a escala existente através da UI (edições de turno não aplicadas).
- Não é possível incluir manualmente plantões pelo frontend.
- A importação de arquivos XLSX só funciona se o arquivo estiver no formato esperado; XLSX com formato diferente pode falhar.

Consulte [PROJECT_STATUS.md](PROJECT_STATUS.md) para o estado detalhado, roadmap e ações pendentes.

## Documentação

- [QUICKSTART.md](QUICKSTART.md) - Guia de início rápido
- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Status atual e roadmap
- [docs/architecture.md](docs/architecture.md) - Detalhes de arquitetura
- [docs/homelab_deploy.md](docs/homelab_deploy.md) - Guia de implantação homelab
- [docs/operations.md](docs/operations.md) - Runbook operacional curto do CT 102
- [docs/backup_restore.md](docs/backup_restore.md) - Backup e restore do PostgreSQL do AgentEscala
- [docs/assumptions.md](docs/assumptions.md) - Decisões técnicas e premissas

## Licença

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

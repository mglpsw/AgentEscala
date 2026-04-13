# Guia de Início Rápido

Este guia coloca o AgentEscala para rodar em menos de 5 minutos.

## Pré-requisitos

- Docker e Docker Compose instalados
- Git

## Passo a passo

### 1. Clone o repositório

```bash
git clone https://github.com/mglpsw/AgentEscala.git
cd AgentEscala
```

### 2. Suba a aplicação

```bash
docker-compose up -d
```

Isso inicia:
- Banco PostgreSQL na porta 5432
- Backend FastAPI na porta 8000

As migrações são aplicadas automaticamente antes de a API subir. Aguarde os serviços ficarem saudáveis (cerca de 10–20 segundos).

### 3. Execute o seed (senha: `password123`)

```bash
docker-compose exec backend python -m backend.seed
```

Isso cria:
- 1 usuário admin
- 5 usuários agente
- 90 turnos (30 dias × 3 turnos/dia)
- 3 solicitações de troca de exemplo

### 4. Acesse a aplicação

- **Documentação da API**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Raiz da API**: http://localhost:8000

### 5. Teste rapidamente

#### Ver todos os turnos
```bash
curl http://localhost:8000/shifts
```

#### Exportar turnos para Excel
```bash
curl http://localhost:8000/shifts/export/excel -o shifts.xlsx
```

#### Exportar turnos para ICS
```bash
curl http://localhost:8000/shifts/export/ics -o shifts.ics
```

#### Ver trocas pendentes
```bash
curl http://localhost:8000/swaps/pending
```

#### Aprovar uma troca (como admin, user_id=1)
```bash
curl -X POST "http://localhost:8000/swaps/1/approve?admin_id=1" \
  -H "Content-Type: application/json" \
  -d '{"admin_notes": "Aprovado"}'
```

### 6. Explore a API

Abra http://localhost:8000/docs no navegador para usar a documentação interativa (Swagger UI).

## Credenciais de exemplo

Após o seed, você terá:

**Admin**:
- E-mail: admin@agentescala.com
- Nome: Admin User
- Senha: password123

**Agentes**:
- alice@agentescala.com (Alice Silva)
- bob@agentescala.com (Bob Santos)
- carol@agentescala.com (Carol Oliveira)
- david@agentescala.com (David Costa)
- eve@agentescala.com (Eve Martins)
- Senha para todos os usuários de exemplo: password123

## Comandos úteis

### Ver logs
```bash
docker-compose logs -f backend
```

### Parar aplicação
```bash
docker-compose down
```

### Reiniciar backend
```bash
docker-compose restart backend
```

### Resetar banco
```bash
docker-compose down -v
docker-compose up -d
docker-compose exec backend python -m backend.seed
```

### Acessar o banco direto
```bash
docker-compose exec db psql -U agentescala -d agentescala
```

## Solução de problemas

### Backend não inicia
Verifique se o banco está saudável:
```bash
docker-compose ps
```

### Erros de conexão com o banco
Garanta que o container do banco está rodando:
```bash
docker-compose up -d db
```

### Porta em uso
Se a porta 8000 ou 5432 já estiver ocupada, ajuste `docker-compose.yml` para usar outras portas.

## Próximos passos

- Leia [README.md](README.md) para a documentação completa de funcionalidades
- Veja [PROJECT_STATUS.md](PROJECT_STATUS.md) para o status atual
- Consulte [docs/architecture.md](docs/architecture.md) para detalhes técnicos
- Revise [docs/homelab_deploy.md](docs/homelab_deploy.md) para implantação em produção

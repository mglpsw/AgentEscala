# Checklist de Validação do MVP do AgentEscala

Use esta checklist para validar a implementação completa do MVP.

## Validação de pré-requisitos

- [ ] Docker instalado (`docker --version`)
- [ ] Docker Compose instalado (`docker-compose --version`)
- [ ] Repositório clonado
- [ ] Estar na raiz do projeto

## Validação em desenvolvimento local

### 1. Subir a aplicação

```bash
cd /path/to/AgentEscala
docker-compose up -d
```

**Esperado:**
- Container do PostgreSQL sobe
- Container do backend sobe após o DB ficar saudável
- Migrações Alembic rodam automaticamente antes da API iniciar
- Sem mensagens de erro

**Validação:**
```bash
docker-compose ps
# Ambos containers devem estar "Up" e saudáveis
```

### 2. Checar logs

```bash
docker-compose logs backend
```

**Esperado:**
- Sem mensagens de erro
- Mensagem "Application startup complete"
- Uvicorn rodando na porta 8000

### 3. Health check

```bash
curl http://localhost:8000/health
```

**Resposta esperada:**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-13T...",
  "version": "1.0.0"
}
```

### 4. Documentação da API

Abra no navegador: http://localhost:8000/docs

**Esperado:**
- Swagger UI carrega
- Três seções visíveis: users, shifts, swaps
- Todos os endpoints listados com documentação

### 5. Seed do banco

```bash
docker-compose exec backend python -m backend.seed
```

**Saída esperada:**
- "Inicializando banco de dados..."
- "Criando usuários..."
- "Criando turnos..."
- "Criando solicitações de troca de exemplo..."
- "Seed concluído"
- Sem erros
- Senha padrão para todos os usuários: `password123`

**Validação:**
```bash
curl http://localhost:8000/users/
```

**Esperado:** array JSON com 6 usuários (1 admin + 5 agentes)

### 6. Operações básicas da API

**Listar turnos:**
```bash
curl http://localhost:8000/shifts/ | jq '.[:2]'
```

**Esperado:** array JSON com objetos de turno

**Obter um turno:**
```bash
curl http://localhost:8000/shifts/1
```

**Esperado:** objeto de turno com informações do agente

**Listar trocas pendentes:**
```bash
curl http://localhost:8000/swaps/pending
```

**Esperado:** array JSON com solicitações de troca pendentes

### 7. Exportação Excel

```bash
curl http://localhost:8000/shifts/export/excel -o test_shifts.xlsx
```

**Esperado:**
- Arquivo `test_shifts.xlsx` gerado
- Tamanho do arquivo > 0 bytes
- Abre em Excel/LibreOffice

**Validação:**
```bash
ls -lh test_shifts.xlsx
# Deve mostrar tamanho ~5-15KB
```

### 8. Exportação ICS

```bash
curl http://localhost:8000/shifts/export/ics -o test_shifts.ics
```

**Esperado:**
- Arquivo `test_shifts.ics` gerado
- Tamanho do arquivo > 0 bytes
- Formato iCalendar válido

**Validação:**
```bash
head -5 test_shifts.ics
# Deve começar com "BEGIN:VCALENDAR"
```

### 9. Fluxo de aprovação de trocas

**Criar uma solicitação de troca:**
```bash
curl -X POST "http://localhost:8000/swaps?requester_id=2" \
  -H "Content-Type: application/json" \
  -d '{
    "target_agent_id": 3,
    "origin_shift_id": 1,
    "target_shift_id": 2,
    "reason": "Teste de troca"
  }'
```

**Esperado:** resposta JSON com a solicitação (status: "pending")

**Aprovar a troca (como admin):**
```bash
curl -X POST "http://localhost:8000/swaps/4/approve?admin_id=1" \
  -H "Content-Type: application/json" \
  -d '{"admin_notes": "Aprovado para teste"}'
```

**Esperado:**
- Status alterado para "approved"
- `reviewed_by` definido como 1
- Turnos com agentes trocados

**Verificar execução da troca:**
```bash
# Confirmar que os turnos 1 e 2 trocaram de agente
curl http://localhost:8000/shifts/1
curl http://localhost:8000/shifts/2
```

### 10. Script de validação

```bash
docker-compose exec backend python -m backend.validate
```

**Saída esperada:**
- "=== Validação do MVP AgentEscala ==="
- Todas as checagens com "✓"
- "O MVP está funcional e pronto para uso!"
- Código de saída 0

## Validação de implantação em homelab

### 1. Conferir pré-requisitos

```bash
# Verificar rede do Traefik
docker network inspect traefik-public

# Esperado: rede existe com external: true
```

### 2. Configuração

```bash
cd infra
cp .env.homelab.example .env.homelab
nano .env.homelab
```

**Edições necessárias:**
- [ ] POSTGRES_PASSWORD alterado
- [ ] SECRET_KEY gerado e definido
- [ ] ADMIN_EMAIL definido
- [ ] DOMAIN ajustado para seu domínio
- [ ] TRAEFIK_NETWORK de acordo com seu ambiente

### 3. Deploy

```bash
./infra/scripts/couple_to_homelab.sh --build
```

**Esperado:**
- Script valida a configuração
- Imagem é construída com sucesso
- Containers sobem
- Mensagem "=== Deploy concluído ==="

### 4. Verificar deploy

```bash
docker-compose -f infra/docker-compose.homelab.yml ps
```

**Esperado:**
- Ambos containers "Up"
- Backend com status "healthy"

### 5. Acesso via domínio

```bash
curl https://agentescala.seudominio.com/health
```

**Esperado:**
- Conexão HTTPS ok (certificado SSL válido)
- Resposta JSON com status "healthy"

### 6. Traefik Dashboard

Abrir: https://traefik.seudominio.com/dashboard/

**Esperado:**
- Roteador do AgentEscala visível
- Status verde (healthy)
- Domínio e entrypoint corretos

## Validação de qualidade de código

### 1. Sintaxe Python

```bash
find backend -name "*.py" -exec python3 -m py_compile {} \;
```

**Esperado:** sem erros de sintaxe

### 2. Estrutura de arquivos

```bash
tree -L 2 -I '__pycache__|*.pyc|.git'
```

**Estrutura esperada:**
```
.
├── backend/
│   ├── api/
│   ├── config/
│   ├── models/
│   ├── services/
│   ├── utils/
│   └── main.py
├── docs/
├── infra/
├── docker-compose.yml
└── Dockerfile
```

### 3. Documentação presente

- [ ] README.md existe e é completo
- [ ] QUICKSTART.md existe com passo a passo
- [ ] PROJECT_STATUS.md existe com status atual
- [ ] IMPLEMENTATION_SUMMARY.md existe com detalhes de código
- [ ] docs/architecture.md existe
- [ ] docs/assumptions.md existe
- [ ] docs/homelab_deploy.md existe

## Validação de requisitos funcionais

- [x] **Backend funcional**: FastAPI rodando com todos os endpoints
- [x] **Banco de dados**: PostgreSQL com modelos e relacionamentos corretos
- [x] **Gestão de Usuários**: CRUD funcionando
- [x] **Gestão de Turnos**: CRUD funcionando
- [x] **Fluxo de Trocas**: criar, aprovar, rejeitar, cancelar funcionando
- [x] **Exportação Excel**: gera arquivos profissionais válidos
- [x] **Exportação ICS**: gera arquivos iCalendar válidos
- [x] **Aprovação do Admin**: trocas exigem aprovação
- [x] **Execução da Troca**: turnos são trocados na aprovação
- [x] **Health Check**: endpoint responde corretamente
- [x] **Docker Local**: subida em um comando
- [x] **Docker Homelab**: script de deploy funciona
- [x] **Documentação**: completa e atual
- [x] **Seed**: criação de dados de exemplo funciona
- [x] **Validação**: script de validação passa

## Validação de requisitos não funcionais

- [x] **Código limpo**: arquitetura em três camadas implementada
- [x] **Separação de responsabilidades**: API, Services, Models separados
- [x] **Segurança de tipos**: modelos Pydantic para validação
- [x] **Tratamento de erros**: HTTPException com códigos corretos
- [x] **Documentação**: docs automáticas da API disponíveis
- [x] **Logging**: Uvicorn registra todas as requisições
- [x] **Segurança**: banco em rede isolada
- [x] **SSL/TLS**: labels do Traefik configuradas
- [x] **Health Checks**: verificações de DB e backend
- [x] **Restart Policy**: reinício automático configurado

## Limitações conhecidas (esperadas)

- [ ] Autenticação não aplicada (login JWT disponível; endpoints ainda aceitam ids)
- [ ] Sem frontend (futuro)
- [ ] Sem testes (futuro)
- [ ] Sem notificações por e-mail (futuro)
- [ ] Fuso único (UTC) (futuro)

## Registro de problemas

Se alguma validação falhar:

1. Anote qual passo falhou
2. Verifique logs: `docker-compose logs`
3. Revise configuração: arquivos `.env`
4. Consulte issues no GitHub: https://github.com/mglpsw/AgentEscala/issues
5. Revise a documentação em `/docs`

## Critério de sucesso

✅ **O MVP está completo quando:**
- Todos os passos de "Validação em desenvolvimento local" passam
- Todos os "Requisitos Funcionais" estão validados
- Documentação está completa e atual
- Código está limpo e segue a arquitetura
- Deploy em homelab é possível com sucesso

## Comando final de validação

Execute todas as validações em sequência:

```bash
# Start local
docker-compose up -d

# Wait for startup
sleep 10

# Seed
docker-compose exec backend python -m backend.seed

# Validate
docker-compose exec backend python -m backend.validate

# Test API
curl http://localhost:8000/health
curl http://localhost:8000/users/
curl http://localhost:8000/shifts/

# Test exports
curl http://localhost:8000/shifts/export/excel -o test.xlsx
curl http://localhost:8000/shifts/export/ics -o test.ics

# Verify files created
ls -lh test.xlsx test.ics

# Check documentation
ls -1 *.md docs/*.md
```

**Se tudo passar:** ✅ O MVP está completo e funcional!

# CONTEXT_AGENTESCALA_COMPLETO — Contexto Unificado para Implementação
# Para: Gemini Code Assist / Claude Code / GitHub Copilot Chat
# Projeto: AgentEscala — Sistema de Gestão de Plantões Médicos

---

## 1. O QUE É O PROJETO

AgentEscala é um sistema de gestão e troca de plantões para equipes médicas.
O backend está funcional e rodando em produção no CT 102 (homelab).
As próximas frentes são expansões sobre uma base já estável.

**Stack atual (não alterar sem instrução explícita):**
- Backend: FastAPI + Python 3.11, porta 8000
- Banco: PostgreSQL 15
- ORM: SQLAlchemy + Alembic (migrations automáticas no boot)
- Auth: JWT (access token 24h, sem refresh ainda)
- Frontend: React + Vite + Tailwind (servido via FastAPI StaticFiles)
- Deploy: Docker Compose, homelab CT 102, domínio `escalas.ks-sm.net:9443`

**Estrutura do repositório:**
```
AgentEscala/
├── backend/
│   ├── api/routers/     ← users.py, shifts.py, swaps.py, auth.py
│   ├── config/          ← settings.py, database.py, auth.py (deps JWT)
│   ├── models/          ← user.py, shift.py, swap_request.py
│   ├── services/        ← user_service.py, shift_service.py, swap_service.py
│   ├── utils/           ← excel_exporter.py, ics_exporter.py
│   ├── alembic/versions/← 001_initial_tables.py (já existe)
│   ├── main.py
│   ├── seed.py
│   └── requirements.txt
├── frontend/src/
│   ├── pages/           ← CalendarPage, ShiftsPage, SwapsPage
│   ├── components/
│   └── hooks/
├── infra/
├── docker-compose.yml
└── Dockerfile
```

**Modelo User atual (simplificado):**
```python
id, email, name, role (admin|agent), hashed_password, is_active, created_at, updated_at
```

**Modelos existentes:** User, Shift, SwapRequest — não modificar estrutura existente.

---

## 2. REGRAS OBRIGATÓRIAS PARA QUALQUER IMPLEMENTAÇÃO

- NÃO modificar migrations já existentes (001_initial_tables.py)
- NÃO alterar docker-compose.yml sem instrução explícita
- NÃO quebrar endpoints de API existentes (contratos atuais devem continuar funcionando)
- Toda nova migration deve ter `upgrade()` E `downgrade()` corretos
- Toda nova dependência Python vai em `backend/requirements.txt`
- Toda nova dependência Node vai via `npm install --save` (não editar package.json manual)
- Nomes de variáveis, funções, classes e arquivos: inglês snake_case
- Comentários de regra de negócio: português
- Commits no formato: `feat(módulo): descrição curta em português`

---

## 3. FRENTES A IMPLEMENTAR (em ordem de prioridade)

---

### FRENTE A — Modelo de Usuário Médico Completo
**Migration:** `002_expand_user_medical_fields.py`

Expandir o modelo `User` com campos para cadastro de médicos brasileiros.

**Campos obrigatórios (NOT NULL) a adicionar:**
| Campo | Tipo DB | Validação |
|---|---|---|
| `cpf` | VARCHAR(14) UNIQUE | formato `000.000.000-00`, validar dígitos verificadores |
| `crm` | VARCHAR(20) | somente dígitos |
| `crm_uf` | CHAR(2) | uma das 27 UFs brasileiras válidas |
| `birth_date` | DATE | não futura, médico >= 18 anos |
| `nationality` | VARCHAR(100) | default `"Brasileira"` |

**Campos opcionais (NULLABLE) a adicionar:**
| Campo | Tipo DB | Observação |
|---|---|---|
| `rg` | VARCHAR(20) | |
| `rg_issued_at` | DATE | |
| `crm_issued_at` | DATE | |
| `cns` | VARCHAR(20) UNIQUE | Cartão Nacional de Saúde, 15 dígitos, algoritmo MS |
| `phone` | VARCHAR(20) | |
| `specialty` | VARCHAR(100) | especialidade médica |
| `avatar_url` | TEXT | |

**Validações de negócio (em `UserService`):**
- CPF: remover formatação, validar 11 dígitos, calcular dígitos verificadores, rejeitar todos iguais (ex: 111.111.111-11)
- CRM: só dígitos, 4-8 caracteres
- UF: validar contra lista `["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]`
- CNS: algoritmo oficial do Ministério da Saúde (módulo 11, cartões iniciando com 1,2,7,8,9)

**Expandir `role` de 2 para 3 valores:**
```python
class UserRole(str, Enum):
    admin  = "admin"   # acesso total
    agent  = "agent"   # médico: ver próprios turnos, solicitar trocas
    viewer = "viewer"  # somente leitura
```

**Schemas Pydantic:**
- `UserCreate`: todos os campos obrigatórios + opcionais, validações inline
- `UserUpdate`: todos opcionais para PATCH parcial
- `UserResponse`: nunca expor `hashed_password`; CPF mascarado para não-admin (`000.***.***-00`)

**Novos endpoints:**
- `GET /users/search?q=` — busca por nome, CRM ou CPF (admin)
- `POST /users/{id}/activate` — reativar usuário (admin)
- Adicionar paginação em `GET /users/` (`?skip=0&limit=20`)

---

### FRENTE B — Auth Endurecida
**Migration:** `003_auth_blacklist_roles.py`

**1. Refresh Token com Blacklist no PostgreSQL:**

Novo modelo `BlacklistedToken`:
```
id, jti (UNIQUE), token_type, user_id (FK), blacklisted_at, expires_at
```

Fluxo de tokens:
- `POST /auth/login` → retorna `access_token` (15 min) + `refresh_token` (7 dias), cada um com `jti` (uuid4) embutido
- `POST /auth/refresh` → valida refresh, verifica jti não está na blacklist, gera novos tokens, revoga o refresh antigo
- `POST /auth/logout` → adiciona jti do access (e do refresh, se enviado) na blacklist
- `get_current_user` dependency → decodifica JWT + verifica blacklist antes de autorizar

Cleanup: `DELETE FROM blacklisted_tokens WHERE expires_at < NOW()` — chamar via endpoint admin ou background task.

**2. Rate Limiting no Login:**
```python
# pip install slowapi
@limiter.limit("5/minute")  # por IP
async def login(...): ...
```

**3. Dependências de Autorização:**
```python
require_admin           # só UserRole.admin
require_agent_or_admin  # UserRole.admin ou UserRole.agent (não viewer)
require_authenticated   # qualquer autenticado
require_admin_or_self   # admin ou próprio usuário (para /users/{id})
```

**Variáveis de ambiente:**
```
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
LOGIN_RATE_LIMIT=5/minute
```

---

### FRENTE C — Exportações e Calendário
**Migration:** `004_calendar_tokens.py`

**1. Excel Profissional da Escala:**

Endpoint: `GET /shifts/export/excel?format=schedule|list&month=&year=`

Formato `schedule`:
- Aba "Escala Mensal": grade onde linhas = dias do mês, colunas = médicos
- Células coloridas por período: manhã (amarelo), tarde (laranja), noite (azul escuro)
- Totais de horas por médico no rodapé
- Aba "Lista de Plantões": tabela detalhada com Médico, CRM, UF, Data, Início, Fim, Duração, Local
- Aba "Resumo": total de plantões e horas por médico

**2. Feed iCalendar para subscrição:**

Novo modelo `CalendarToken`: `id, user_id (UNIQUE FK), token (uuid4 UNIQUE), is_active, last_accessed_at`

Endpoints:
- `POST /calendar/subscribe` → gera ou rotaciona token do usuário autenticado
- `GET /calendar/subscribe/{token}` → **público**, sem auth, retorna feed ICS atualizado
- `DELETE /calendar/subscribe` → revoga link

Retorno do POST:
```json
{
  "webcal_url": "webcal://escalas.ks-sm.net/calendar/subscribe/{token}",
  "https_url": "https://escalas.ks-sm.net/calendar/subscribe/{token}",
  "instructions": {
    "icloud": "Calendário → Adicionar Conta → Outro → Adicionar Calendário Inscrito → cole o webcal_url",
    "google": "Outros calendários (+) → A partir do URL → cole o https_url"
  }
}
```

Gerar feed com `icalendar`: incluir `x-wr-calname`, `refresh-interval PT1H`, eventos com `summary`, `dtstart`, `dtend`, `location`, `description` com CRM do médico.

**3. Google Calendar OAuth2 (opcional, implementar após os itens 1 e 2):**

Novo modelo `GoogleCalendarToken`: `user_id (UNIQUE FK), access_token (encrypted), refresh_token (encrypted), calendar_id`

Criptografar tokens com `cryptography.fernet.Fernet` antes de salvar.
Endpoints: `GET /integrations/google/authorize`, `GET /integrations/google/callback`, `DELETE /integrations/google`

Ao criar/atualizar/deletar turno no `ShiftService`, chamar `google_calendar_service.sync_shift()` em try/except (não bloquear a resposta se falhar).

**Novas dependências:** `google-api-python-client`, `google-auth-oauthlib`, `cryptography`

---

### FRENTE D — Notificações em Tela e Bot Telegram
**Migration:** `005_notifications_telegram.py`

**1. Modelo `Notification`:**
```
id, user_id (FK destinatário), type (enum), title, body, link,
reference_id, reference_type, is_read (False), created_at, read_at
```

Tipos de notificação: `swap_requested`, `swap_approved`, `swap_rejected`, `swap_cancelled`, `shift_created`, `shift_updated`, `shift_deleted`, `user_registered`, `chat_message`

**2. WebSocket de notificações:**

Endpoint: `GET /ws/notifications?token={jwt}`

Fluxo:
- Validar JWT como query param (sem header Authorization — WebSocket não suporta)
- Enviar notificações não lidas ao conectar
- Manter conexão com heartbeat (cliente envia "ping" a cada 30s)
- Ao criar notificação: salvar no DB + `await manager.send_to_user(user_id, payload)`

**3. Endpoints REST:**
- `GET /notifications?unread_only=false`
- `PATCH /notifications/{id}/read`
- `POST /notifications/read-all`

**4. Integrar nos serviços existentes (adicionar ao final de cada método, não alterar lógica):**
- `SwapService.create_swap` → notificar admins
- `SwapService.approve_swap` → notificar solicitante + agente alvo
- `SwapService.reject_swap` → notificar solicitante
- `ShiftService.create_shift` / `update_shift` / `delete_shift` → notificar agente

**5. Bot Telegram:**

Modelo `TelegramConfig`: `user_id (UNIQUE FK), telegram_chat_id, is_active, notify_*` (flags por tipo)

Comandos: `/start`, `/conectar {token}`, `/meus_plantoes`, `/proximos`, `/status`, `/desconectar`, `/ajuda`

Endpoints: `POST /telegram/link-token` (gera token 15min para vinculação), `POST /telegram/webhook` (recebe updates do Telegram, validar `X-Telegram-Bot-Api-Secret-Token`)

Usar `httpx` para enviar mensagens: `POST https://api.telegram.org/bot{TOKEN}/sendMessage`

**Frontend — `NotificationBell.jsx`:**
- Badge com contagem de não lidas no header
- Click abre painel lateral com lista de notificações
- WebSocket conecta ao montar o componente
- Toast ao receber nova notificação

**Variáveis:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`

---

### FRENTE E — OCR com IA para Importação de Escalas
**Migration:** `007_ocr_imports.py`

Esta é a feature central. Médicos fotografam ou escaneiam a escala e o sistema importa automaticamente.

**Pipeline:**
```
Upload (PDF/Imagem)
→ Detector de tipo (MIME real, não extensão)
→ Extrator: pdfplumber (PDF digital) ou Tesseract (imagem/PDF escaneado)
→ Pré-processamento de imagem (grayscale, contraste, sharpen)
→ Claude API: analisa layout e retorna JSON estruturado
→ Parser: normaliza datas e horários em múltiplos formatos
→ Name Matcher: fuzzy match (rapidfuzz) nome extraído → usuário na DB
→ Staging: salva para revisão humana
→ Revisão: admin corrige linhas com baixa confiança
→ Confirmação: cria Shifts reais, detecta duplicatas
```

**Modelos:**

`OcrImport`: `id, uploaded_by (FK), original_filename, file_type, file_size_bytes, file_path, status (enum), detected_month, detected_year, total_rows, matched_rows, unmatched_rows, raw_text, ai_analysis (JSONB), error_message, created_at, processed_at, confirmed_at, confirmed_by`

Status enum: `pending → processing → review → confirmed | failed`

`OcrImportRow`: `id, import_id (FK), row_index, raw_name, raw_date, raw_start_time, raw_end_time, raw_location, raw_extra (JSONB), parsed_date, parsed_start_time, parsed_end_time, matched_user_id (FK nullable), match_confidence (float), match_alternatives (JSONB), status (enum), reviewer_note, created_shift_id (FK nullable)`

Row status enum: `matched (≥75% confiança) | review (<75%) | rejected | confirmed`

**Módulos a criar em `backend/ocr/`:**

`detector.py` — detectar MIME real com `python-magic`, validar tamanho (max 50MB), detectar se PDF é digital (pdfplumber extrai > 100 chars)

`pdf_parser.py` — pdfplumber: extrair texto + tabelas (`page.extract_tables()`)

`image_parser.py` — Tesseract: pré-processar imagem (grayscale→contraste→sharpen), `pytesseract.image_to_string(lang='por+eng', config='--psm 6')`, `pdf2image` para PDF escaneado

`layout_analyzer.py` — Claude API com system prompt especializado em escalas médicas brasileiras, retorna JSON com: `format, detected_month, detected_year, headers, rows[{raw_name, raw_date, raw_start_time, raw_end_time, raw_location, confidence}], warnings`

`row_parser.py` — parsear datas em formatos: `"15/04/2026"`, `"15/04"`, `"15 ABR"`, `"15"`. Parsear horários: `"07:00"`, `"7h"`, `"7h30"`, `"700"`. Usar `context_month`/`context_year` do `OcrImport` quando data incompleta.

`name_matcher.py` — normalizar (remover Dr/Dra/Prof, acentos, lowercase), `rapidfuzz.process.extract(scorer=fuzz.WRatio, limit=3)`, retornar `{matched_user_id, match_confidence, alternatives, status}`. Threshold: 0.75.

`import_service.py` — orquestrar pipeline completo de forma assíncrona, atualizar status a cada etapa, `confirm_import()` cria Shifts reais verificando duplicatas (mesmo `agent_id + start_time`).

**Endpoints:**
- `POST /ocr/imports` — upload multipart, dispara pipeline via `BackgroundTasks`, retorna `{import_id, status}`
- `GET /ocr/imports` — lista imports (admin)
- `GET /ocr/imports/{id}` — detalhe com todas as linhas
- `PATCH /ocr/imports/{id}/rows/{row_id}` — corrigir match manualmente
- `POST /ocr/imports/{id}/confirm` — criar turnos reais
- `DELETE /ocr/imports/{id}` — cancelar (só se não confirmado)

**Frontend — `OcrImportPage.jsx`:**
1. Área de upload (drag & drop, aceita PDF/JPG/PNG/WEBP, máx 50MB)
2. Progress indicator (polling `GET /ocr/imports/{id}` a cada 2s durante processamento)
3. Tabela de revisão: verde (≥75%), amarelo (<75%), vermelho (sem match); dropdown para selecionar médico correto por linha
4. Botão "Confirmar Importação" com modal de resumo antes de executar

**Dependências Python:** `pdfplumber`, `pdf2image`, `pytesseract`, `Pillow`, `python-magic`, `rapidfuzz`, `anthropic`

**Dependências de sistema (Dockerfile):**
```dockerfile
RUN apt-get update && apt-get install -y \
    tesseract-ocr tesseract-ocr-por poppler-utils libmagic1 \
    && rm -rf /var/lib/apt/lists/*
```

**Variáveis:** `ANTHROPIC_API_KEY`, `OCR_UPLOAD_DIR=/app/uploads/ocr`

---

### FRENTE F — Chat Privado Criptografado
**Migration:** `006_chat.py`

**Modelos:**

`Conversation`: `id, user_a_id (FK), user_b_id (FK), created_at, last_message_at`
→ UniqueConstraint em `(user_a_id, user_b_id)`, sempre ordenar `a < b` ao criar

`Message`: `id, conversation_id (FK), sender_id (FK), content_encrypted (BYTEA), is_deleted (False), is_read (False), created_at, updated_at`

**Criptografia (backend/utils/encryption.py):**
```python
# Fernet (AES-128-CBC) com chave derivada por conversa via HKDF-SHA256
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import base64

def derive_conversation_key(master_key: bytes, conversation_id: int) -> bytes:
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                 info=f"conv_{conversation_id}".encode())
    return base64.urlsafe_b64encode(hkdf.derive(master_key))
```

Documentar claramente: proteção em repouso (DB breach), mas não E2E puro (servidor conhece MASTER_KEY). Admins NÃO têm endpoint de leitura de conversas alheias.

**Regras de negócio:**
- Máximo 2000 caracteres por mensagem
- Soft delete: apenas remetente, dentro de 10 minutos → substituir conteúdo por `"[mensagem removida]"` criptografado
- `mark_as_read()`: marca mensagens do outro participante como lidas

**WebSocket:** `GET /ws/chat/{conversation_id}?token={jwt}`
- Eventos enviados: `{type: "message", ...}`, `{type: "read", reader_id}`, `{type: "pong"}`
- Ao receber mensagem nova: salvar criptografado, descriptografar, broadcast para sala, disparar notificação para outro participante

**Endpoints REST:**
- `GET /conversations` — lista conversas com preview (última mensagem descriptografada, contagem não lidas)
- `POST /conversations` — `{target_user_id}` → cria ou retorna conversa existente
- `GET /conversations/{id}/messages?skip=0&limit=50` — histórico descriptografado, paginado
- `POST /conversations/{id}/messages` — alternativa REST ao WS
- `DELETE /conversations/{id}/messages/{msg_id}` — soft delete
- `POST /conversations/{id}/read` — marcar como lido

**Frontend — `ChatPage.jsx`:**
- Sidebar esquerda: lista de conversas (avatar, nome, preview, badge não lidas)
- Painel direito: histórico com bolhas (próprias à direita, recebidas à esquerda)
- Input: `Enter` envia, `Shift+Enter` nova linha
- Rota: `/chat` e `/chat/:conversationId`

**Variável:** `MASTER_ENCRYPTION_KEY` (32 bytes hex, gerar com `python -c "import secrets; print(secrets.token_hex(32))"`)

---

## 4. MAPA DE MIGRATIONS (ordem obrigatória)

```
001_initial_tables (já existe — NÃO TOCAR)
002_expand_user_medical_fields     ← FRENTE A
003_auth_blacklist_roles           ← FRENTE B
004_calendar_tokens                ← FRENTE C
005_notifications_telegram         ← FRENTE D
006_chat                           ← FRENTE F
007_ocr_imports                    ← FRENTE E
```

---

## 5. ORDEM DE IMPLEMENTAÇÃO RECOMENDADA

```
1. FRENTE B (Auth) — desbloqueia segurança para tudo mais
2. FRENTE A (Modelo Usuário) — base para todas as features médicas
3. FRENTE E (OCR) — feature central do produto
4. FRENTE C (Exports/Calendário) — valor imediato para usuários
5. FRENTE D (Notificações/Bot) — experiência operacional
6. FRENTE F (Chat) — feature de conveniência
```

---

## 6. VARIÁVEIS DE AMBIENTE COMPLETAS (.env)

```env
# Existentes
SECRET_KEY=
DATABASE_URL=postgresql://user:pass@db:5432/agentescala
CORS_ALLOW_ORIGINS=https://escalas.ks-sm.net

# FRENTE B — Auth
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
LOGIN_RATE_LIMIT=5/minute

# FRENTE C — Calendário Google
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=https://escalas.ks-sm.net/integrations/google/callback
FERNET_KEY=

# FRENTE D — Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=

# FRENTE F — Chat
MASTER_ENCRYPTION_KEY=

# FRENTE E — OCR
ANTHROPIC_API_KEY=
OCR_UPLOAD_DIR=/app/uploads/ocr
```

---

## 7. CHECKLIST DE VALIDAÇÃO APÓS CADA FRENTE

```bash
# Sobe sem erro
docker-compose up -d --build

# Migrations aplicam sem erro
docker-compose exec backend alembic upgrade head

# Testes passam
docker-compose exec backend python -m pytest

# Health responde
curl http://localhost:8000/health
# Esperado: {"status": "ok", ...}

# Seed funciona
docker-compose exec backend python -m backend.seed
```

---

## 8. INSTRUÇÃO FINAL PARA O ASSISTENTE DE IA

Implemente as frentes descritas acima no repositório AgentEscala, seguindo estas regras:

1. Implemente UMA frente por vez, na ordem recomendada da seção 6
2. Antes de qualquer código, crie a branch: `git checkout -b feat/<nome> development`
3. Nunca modifique arquivos fora do escopo da frente atual
4. Nunca altere migrations já existentes
5. Ao final de cada frente, execute o checklist da seção 7
6. Sugira commit semântico: `feat(módulo): descrição em português`

Comece pela **FRENTE B — Auth Endurecida**, pois é pré-requisito de segurança para as demais.

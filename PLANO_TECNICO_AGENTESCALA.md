Aqui está o plano completo. Vou entregar primeiro o diagnóstico e arquitetura visual, depois o documento detalhado de todas as fases.Agora o plano completo, fase a fase:

---

## Resumo executivo

O backend do AgentEscala está sólido e validado em runtime real. O que falta para um release utilizável são três peças: **Web UI interativa**, **engine de OCR para escalas médicas** e **acabamento de produção** (refresh token, auditoria, testes mais amplos). As três peças são independentes e podem correr em paralelo, mas a ordem ideal é: finalizar backend → Web UI base → OCR → integração e release.

---

## Diagnóstico do estado atual

**O que está sólido:**
- Backend FastAPI com auth JWT aplicada nos endpoints sensíveis
- CRUD completo de usuários, turnos e trocas
- Fluxo de swap com aprovação admin funcionando
- Exportação Excel e ICS
- Seed, Alembic, healthcheck, métricas Prometheus
- Deploy isolado no CT 102 validado em runtime real
- Testes mínimos passando (4 passed)

**Gargalos que bloqueiam o release:**
- Sem Web UI — nenhum médico consegue usar o sistema sem cliente HTTP
- Sem OCR — a entrada de dados ainda depende de CSV/XLSX manual
- Sem refresh token — sessões expiram em 24h sem renovação
- Cobertura de testes enxuta — risco de regressão ao escalar

**O que pode ficar para depois sem bloquear o release:**
- Bot Telegram
- Multi-timezone
- CI/CD automatizado
- Email notifications

---

## Roadmap por fases

### Fase 0 — Endurecimento do backend (1–2 dias, pré-requisito)

Nenhuma nova feature. Só consolidar o que já existe antes de construir UI.

**Tarefas:**
- Implementar refresh token (`POST /auth/refresh`) e endpoint de logout (`POST /auth/logout` com blacklist em memória ou Redis simples)
- Adicionar `ImportService` e modelo `OcrImport` no banco para staging do OCR (tabela: `ocr_imports`, colunas: `id, status, raw_payload, parsed_rows, errors, created_by, confirmed_at`)
- Expandir testes: ao menos 1 teste por router crítico (auth, shifts, swaps, users)
- Atualizar migração Alembic com a nova tabela

**Critério de aceite:** `pytest` passa com cobertura dos 4 routers; refresh token funciona; tabela `ocr_imports` existe no banco.

**Branch sugerida:** `feat/backend-hardening-phase0`

---

### Fase 1 — Web UI base com autenticação e calendário (5–8 dias)

**Stack recomendada:**
- **React 18 + Vite** — bundle rápido, sem framework pesado
- **TanStack Query (React Query)** — cache e sincronização de dados com a API
- **React Router v6** — roteamento client-side
- **FullCalendar** (biblioteca, licença MIT) — calendário mensal/semanal pronto
- **Tailwind CSS** — utilitário, sem CSS custom extenso
- **Axios** com interceptor de JWT — renova token transparentemente

**Estrutura de páginas:**

```
/login              → formulário, POST /auth/login, salva token no localStorage
/calendar           → calendário mensal com os turnos do usuário logado
/shifts             → tabela de turnos com filtros (agente, data, status)
/swaps              → lista de trocas + formulário de nova solicitação
/swaps/pending      → visão admin das trocas pendentes
/import             → upload de arquivo + preview (conecta com OCR na Fase 2)
/admin/users        → CRUD de usuários (só admin)
```

**Componentes principais:**

- `AuthProvider` — contexto React com token, usuário logado e refresh automático
- `ProtectedRoute` — redireciona para `/login` se não autenticado; verifica papel (admin vs agent)
- `ShiftCalendar` — wrapper do FullCalendar consumindo `GET /shifts/` e `GET /shifts/agent/{id}`
- `ShiftTable` — tabela paginada com colunas: médico, início, fim, local, duração; filtros por data e agente
- `SwapCard` — card de troca com status colorido (pending = amarelo, approved = verde, rejected = vermelho)
- `SwapForm` — formulário para solicitar troca: seleciona turno próprio + turno do colega alvo
- `AdminSwapPanel` — lista de pendentes com botões Aprovar / Rejeitar + campo de observação
- `FileUploader` — drag-and-drop de PDF/CSV/XLSX para o fluxo de importação

**Estados da interface:**

```
Não autenticado → /login
Autenticado como agent → calendar, shifts (próprios), swaps (próprias)
Autenticado como admin → tudo acima + admin/users, swaps/pending, import
```

**Chamadas de API mais importantes:**

| Ação | Endpoint |
|---|---|
| Login | `POST /auth/login` |
| Renovar sessão | `POST /auth/refresh` |
| Carregar turnos (calendário) | `GET /shifts/?agent_id=me&from=&to=` |
| Solicitar troca | `POST /swaps/` |
| Aprovar troca | `POST /swaps/{id}/approve` |
| Exportar Excel | `GET /shifts/export/excel` |

**Deploy da UI:**

O Vite gera um bundle estático. Duas opções simples para o homelab:
- Servir o `dist/` com nginx em container adicional no mesmo compose do CT 102
- Ou, mais simples ainda: servir o `dist/` via FastAPI com `StaticFiles` — um único container, sem nginx separado

A opção `StaticFiles` no FastAPI é a mais simples para o homelab: adiciona `app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")` no `main.py` e o compose já resolve.

**Critério de aceite da Fase 1:** médico consegue logar, ver o calendário com os próprios turnos, solicitar uma troca; admin consegue aprovar a troca — tudo pelo navegador, sem cliente HTTP manual.

**Branch:** `feat/web-ui-phase1`

---

### Fase 2 — Engine OCR para escalas médicas (5–10 dias)

Esta é a peça mais complexa. A estratégia é **híbrida e progressiva**: começar com parser estrutural (sem OCR pesado), adicionar OCR para imagens escaneadas somente quando necessário, e usar modelo multimodal apenas como último recurso.

**Arquitetura do pipeline:**

```
Entrada (PDF / imagem / XLSX / CSV)
    │
    ▼
[Detector de tipo de entrada]
    │
    ├── PDF digital (tem texto) ──→ pdfplumber extrai texto + layout
    │                               detect_layout() identifica grade de células
    │
    ├── PDF escaneado / imagem ──→ Tesseract 5 com PSM 6 (bloco de texto uniforme)
    │                               Fallback: Claude Vision via API se Tesseract < 60% confiança
    │
    └── XLSX / CSV ─────────────→ openpyxl / pandas, detecta cabeçalhos automaticamente
    │
    ▼
[Layout Analyzer]
    Identifica: cabeçalho de datas, coluna de nomes, células de turno
    Estratégia: detecta padrão de grade (linhas com hora × colunas com médico)
    │
    ▼
[Row Parser]
    Para cada célula identificada:
    - extrai nome bruto
    - extrai horário início/fim
    - extrai local/setor (se presente)
    - marca incerteza (< 80% match ou campo vazio)
    │
    ▼
[Name Matcher]
    Fuzzy match contra tabela users do banco
    Usa: rapidfuzz (token_sort_ratio ≥ 85 = match automático)
    Abaixo de 85: marca como incerto, propõe candidatos ranqueados
    Nomes sem match algum: marca como UNKNOWN, requer resolução manual
    │
    ▼
[Staging]
    Persiste em ocr_imports com status: draft
    Cada linha tem: raw_text, parsed_name, matched_user_id, match_score,
                    start_time, end_time, location, status (ok/warning/error)
    │
    ▼
[Web UI — Fase de Revisão]
    Tabela de linhas com filtro por status
    Edição inline de campos problemáticos
    Confirmação → chama ShiftService.create() para cada linha aprovada
```

**Módulos e responsabilidades:**

`backend/ocr/`
- `detector.py` — detecta tipo de entrada, decide rota de extração
- `pdf_parser.py` — usa `pdfplumber` para texto digital; devolve lista de células `{text, x, y, width, height}`
- `image_parser.py` — usa Tesseract via `pytesseract`; devolve mesmo contrato de células
- `layout_analyzer.py` — recebe células e identifica grade (linhas = datas, colunas = médicos, ou inverso); usa heurística de alinhamento e frequência de padrões de hora
- `row_parser.py` — extrai campos estruturados de cada célula; normaliza datas (dateutil.parser) e horas (regex `\d{1,2}[:h]\d{2}`)
- `name_matcher.py` — fuzzy match contra lista de médicos do banco; retorna `{user_id, name, score, candidates[]}`
- `import_service.py` — orquestra o pipeline; persiste staging; expõe `confirm(import_id, approved_rows[])` que chama `ShiftService`

**Endpoint OCR:**

```
POST /ocr/parse          → recebe arquivo, retorna import_id e linhas staged
GET  /ocr/imports/{id}   → retorna linhas do staging com status e candidatos
PATCH /ocr/imports/{id}/rows/{row_id} → edição manual de uma linha
POST /ocr/imports/{id}/confirm → confirma, cria shifts das linhas aprovadas
DELETE /ocr/imports/{id} → descarta staging
```

**Dependências novas (conservadoras):**

```
pdfplumber          # extração de PDF digital — leve, sem binários
pytesseract         # wrapper Tesseract — OCR para imagens
Pillow              # manipulação de imagem
rapidfuzz           # fuzzy matching — sem dependência de modelos
python-dateutil     # parsing de datas flexível
```

Tesseract 5 precisa ser instalado no Dockerfile via `apt-get install -y tesseract-ocr tesseract-ocr-por`. O `lang por` cobre nomes médicos em português.

**Fallback multimodal (Claude Vision):**

Somente quando `Tesseract confidence < 60%` em toda a página. Faz chamada `POST /v1/messages` com a imagem em base64, prompt estruturado pedindo JSON de células. Custo controlado: só ativa para páginas que falharam no OCR local. Implementar como flag `OCR_MULTIMODAL_FALLBACK=true` no `.env`.

**Critério de aceite da Fase 2:** upload de uma escala médica em PDF resulta em staging revisável; 80%+ dos nomes são matchados automaticamente; linhas com erro são editáveis na UI; confirmação cria os shifts no banco.

**Branch:** `feat/ocr-engine-phase2`

---

### Fase 3 — Observabilidade e acabamento de release (2–3 dias)

**Métricas Prometheus novas:**

```python
ocr_parse_duration_seconds    # histograma — tempo de parse por tipo de entrada
ocr_match_rate                # gauge — % de nomes matchados automaticamente
ocr_manual_corrections_total  # contador — quantas linhas foram editadas manualmente
ocr_imports_total             # counter com label status (confirmed, discarded)
shift_import_total            # counter — shifts criados via OCR vs manual
```

**Logs estruturados:**

Adicionar `structlog` ou simplesmente JSON logs no FastAPI:
```python
logger.info("ocr.parse", file_type="pdf", pages=3, rows_extracted=42, duration_ms=1200)
logger.info("ocr.match", import_id=..., matched=38, uncertain=3, unmatched=1)
logger.info("ocr.confirm", import_id=..., shifts_created=38, skipped=4)
```

**Dashboard Grafana (CT 200):**

Adicionar o endpoint `/metrics` do CT 102 como target no Prometheus do CT 200. Criar dashboard com:
- Taxa de parse OCR (sucesso/falha por hora)
- Match rate médio dos últimos 7 dias
- Correções manuais por importação (indica qualidade do parser)
- Latência P95 do endpoint `/ocr/parse`

**Trilha de auditoria mínima:**

Adicionar coluna `action_log JSONB` no modelo `OcrImport` — registra cada edição manual com `{user_id, timestamp, field, old_value, new_value}`. Sem tabela separada na v1.

---

## Plano de implementação em etapas

| # | Objetivo | Branch | Validação | Critério de aceite |
|---|---|---|---|---|
| 1 | Refresh token + logout | `feat/auth-refresh` | `pytest test_auth.py` | token renovado sem re-login |
| 2 | Modelo `ocr_imports` + migração | `feat/ocr-model` | `alembic upgrade head` sem erro | tabela existe no DB |
| 3 | Web UI: scaffolding Vite + Tailwind | `feat/ui-scaffold` | `npm run dev` abre tela de login | login funciona |
| 4 | Web UI: calendário e lista de turnos | `feat/ui-calendar` | carrega turnos reais da API | calendário exibe shifts do médico |
| 5 | Web UI: trocas e painel admin | `feat/ui-swaps` | fluxo completo no browser | swap aprovada muda status |
| 6 | OCR: detector + pdf_parser | `feat/ocr-parser` | teste unitário com PDF real | extrai células com coordenadas |
| 7 | OCR: layout_analyzer | `feat/ocr-layout` | teste com escala real | identifica cabeçalhos e grade |
| 8 | OCR: name_matcher + row_parser | `feat/ocr-matcher` | fuzzy match ≥ 80% numa escala real | linhas com score e candidatos |
| 9 | OCR: endpoints REST + staging | `feat/ocr-api` | Postman / httpie | POST /ocr/parse retorna staged rows |
| 10 | Web UI: tela de revisão OCR | `feat/ui-import` | upload → revisão → confirmação | shifts criados no banco |
| 11 | Métricas OCR + logs estruturados | `feat/observability` | `/metrics` retorna novas métricas | Grafana exibe match rate |
| 12 | Testes de integração completos | `feat/tests` | `pytest -v` sem falhas | cobertura mínima dos fluxos críticos |
| 13 | Build estático UI + compose final | `feat/release-prep` | `docker-compose up` sobe tudo | acesso pelo browser via NPM |

---

## Definição de release (v1)

**Obrigatório para chamar de release:**
- Login funciona e sessão se mantém com refresh token
- Médico vê o calendário com os próprios turnos
- Médico solicita troca de turno pela UI
- Admin aprova/rejeita pela UI
- Upload de escala (PDF ou XLSX) funciona e cria shifts após revisão
- Sistema roda estável no CT 102 sem interromper outros serviços
- Healthcheck responde; métricas disponíveis

**Pode ficar para depois:**
- Bot Telegram
- Notificações por e-mail
- Multi-timezone
- CI/CD automático
- Relatórios analíticos

**Riscos residuais aceitáveis na v1:**
- OCR de PDFs muito desestruturados pode exigir correção manual em até 30% das linhas — aceitável, o fluxo de revisão foi projetado para isso
- Sem rate limiting — aceitável no homelab; adicionar antes de expor publicamente
- Refresh token em memória (sem Redis) — reiniciar o backend invalida sessões; aceitável no MVP

---

## Próximos passos imediatos

**Esta semana, em ordem:**

1. Criar branch `feat/auth-refresh` e implementar `POST /auth/refresh` e `POST /auth/logout` — 1 dia
2. Criar migração Alembic com tabela `ocr_imports` — meio dia
3. Iniciar scaffold da Web UI com Vite + React + Tailwind + tela de login conectada à API real — 1 dia
4. Enquanto a UI avança, iniciar `backend/ocr/detector.py` e `pdf_parser.py` com um PDF de escala real como fixture de teste — 1 dia
5. Ao final da semana: PR de revisão do backend hardening, demo da tela de login funcionando no browser

O maior risco é o OCR de layout — escalas médicas variam muito em formato. Recomendo reservar 2–3 PDFs reais de escalas diferentes como fixtures de teste desde o início, para calibrar o `layout_analyzer` antes de construir a UI de revisão.
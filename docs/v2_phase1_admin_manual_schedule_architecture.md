# AgentEscala v2.0 — Fase 1 (Passo 1: endurecimento de acesso e RBAC)

> Documento atualizado para substituir o plano genérico anterior por um plano **baseado no código real do repositório**. O foco aqui é preparar a base com segurança e controle de acesso antes de evoluir regras de negócio (ex.: preferências de plantão).

## Diagnóstico atual

### 1) Modelagem de usuários, autenticação e permissões
- Usuários estão em `backend/models/models.py` com `role` (`admin`, `medico`, `financeiro`, `agent` legado), flag `is_admin` e `is_active`.
- A autenticação JWT está em `backend/api/auth.py` com login/refresh/logout e retorno de `user_role` no login.
- A autorização de admin depende de `require_admin` em `backend/utils/dependencies.py`, que aceita admin por `role == ADMIN` **ou** `is_admin == true`.
- Existe dualidade de fonte de verdade de privilégio (`role` e `is_admin`), o que aumenta risco de inconsistência.

### 2) Endpoints já admin-only (backend)
**Imports (todos admin-only):** `backend/api/schedule_imports.py`
- `POST /schedule-imports/`
- `POST /schedule-imports/{import_id}/validate`
- `GET /schedule-imports/`
- `GET /schedule-imports/{import_id}`
- `GET /schedule-imports/{import_id}/summary`
- `GET /schedule-imports/{import_id}/rows`
- `POST /schedule-imports/{import_id}/confirm`
- `GET /schedule-imports/{import_id}/report`

**Turnos admin-only (parciais):** `backend/api/shifts.py`
- `POST /shifts/`
- `PATCH /shifts/{shift_id}`
- `DELETE /shifts/{shift_id}`
- `GET /shifts/consistency-report`

**Trocas admin-only (parciais):** `backend/api/swaps.py`
- `GET /swaps/pending`
- `GET /swaps/export/excel`
- `POST /swaps/{swap_id}/approve`
- `POST /swaps/{swap_id}/reject`

**Admin de usuários/auditoria:** `backend/api/users.py`
- `GET/POST/PUT/DELETE/PATCH /admin/users...`
- `GET /admin/audit/users`
- além dos endpoints legados admin-only em `/users` (create/list/admins/deactivate)

**Outros admin-only:**
- `POST /api/v1/terminal/action` em `backend/main.py`
- `POST /admin/schedule/validate` em `backend/api/admin_schedule.py`

### 3) Como a importação de escala está protegida hoje
- Proteção está correta no backend: todos os endpoints de import usam `Depends(require_admin)` em `backend/api/schedule_imports.py`.
- A rota de UI `/import` é protegida no frontend por `ProtectedRoute requiredRole="admin"` em `frontend/src/router/app_router.jsx`.
- O menu também oculta “Importar Escala” para não-admin em `frontend/src/components/app_layout.jsx`.

### 4) Como o frontend decide o que mostrar por usuário
- `AuthProvider` define `isAdmin` por `user.role === 'admin' || user.is_admin === true` em `frontend/src/contexts/auth_context.jsx`.
- Rotas admin ficam em bloco dedicado no router (`/import`, `/swaps/pending`, `/admin/users`).
- O menu lateral filtra links admin via `isAdmin`.
- Páginas de calendário/turnos do médico usam `user.id` do contexto para chamar `/shifts/agent/{user.id}`.

### 5) Gaps de segurança e controle de acesso identificados
1. **IDOR em turnos**: backend permite qualquer usuário autenticado consultar turnos de qualquer agente em `GET /shifts/agent/{agent_id}` e também listar todos os turnos em `GET /shifts`.
2. **Exposição ampla de escala**: endpoints de export/lista de `shifts` estão abertos para qualquer autenticado, não apenas admin.
3. **RBAC híbrido e ambíguo**: coexistência de `role` + `is_admin` como decisão efetiva de permissão.
4. **Rate limit de login em memória local** (`backend/utils/rate_limiter.py`): não considera `X-Forwarded-For`, não é distribuído entre réplicas.
5. **Logout/blacklist de refresh em memória** (`backend/utils/token_store.py`): revogação não é persistente entre reinícios.
6. **Cobertura de testes de autorização ainda parcial**: há bons testes para import/admin, mas falta bloqueio explícito para médico consultar `/shifts/agent/{outro_id}`.

### Inconsistências backend x frontend (permissões)
- **Frontend assume isolamento por usuário** (sempre chama `/shifts/agent/{user.id}`), mas **backend não reforça essa restrição**.
- Resultado: um cliente malicioso pode chamar API direta e acessar dados além da UI.
- Conclusão: backend deve ser fonte de verdade e não depender de ocultação de botões/rotas.

---

## Riscos atuais

1. Vazamento de escala entre médicos (confidencialidade de dados operacionais).
2. Escalonamento indevido por inconsistência entre `role` e `is_admin`.
3. Contorno de bloqueios de UI via chamadas HTTP diretas.
4. Mitigação de brute-force limitada em cenários com proxy/replicação.
5. Perda de trilha de segurança de sessão após restart (revogação volátil).

---

## Plano por etapas (PASSO 1 conservador)

### Etapa A — Consolidar RBAC sem quebrar contratos
- Manter compatibilidade com `UserRole` atual, mas definir regra operacional única:
  - **admin efetivo** = `role == admin` (fonte primária)
  - `is_admin` mantido como campo legado/espelho temporário.
- Centralizar helper em `dependencies.py`:
  - `is_effective_admin(user)`
  - `require_admin` passa a usar helper central.
- Não remover papéis existentes neste passo; apenas clarificar e padronizar verificação.

### Etapa B — Backend como fonte de verdade para escopo de dados
- Endurecer `GET /shifts/agent/{agent_id}`:
  - admin acessa qualquer `agent_id`
  - médico só acessa o próprio `current_user.id`
  - senão, `403`.
- Revisar `GET /shifts` e exports (`/shifts/export*`, `/shifts/final-schedule`) com política explícita:
  - opção conservadora recomendada: admin-only para visão global;
  - médicos usam `/me/shifts` como rota oficial de visão própria.
- Preservar resposta/shape quando permitido, evitando quebra de frontend.

### Etapa C — Importação/revisão/confirmação estritamente admin-only (hardening)
- Manter proteção atual dos endpoints (já correta).
- Adicionar testes de regressão para garantir que nenhum endpoint de import perca `require_admin`.
- Documentar no backend README e docs operacionais que import é ação exclusiva de admin.

### Etapa D — Frontend por papel (ocultação + alinhamento)
- Continuar ocultação de rotas/menu admin.
- Ajustar telas de médico para usar apenas `/me/shifts` onde fizer sentido (reduz dependência de endpoint amplo).
- Exibir estado de acesso negado amigável quando API retornar 403.

### Etapa E — Login hardening e auditoria mínima
- Rate limit:
  - manter implementação atual no passo 1 (baixo risco),
  - incluir leitura opcional de IP real via proxy confiável (configurável),
  - adicionar métricas/contadores de bloqueio 429.
- Auditoria:
  - manter `AdminUserAuditLog` para ações de usuários,
  - adicionar logs mínimos de autenticação (sucesso/falha/login bloqueado por rate-limit).
  - não criar grandes mudanças de banco agora; priorizar logs estruturados.

### Etapa F — Testes automatizados de autorização e regressão
- Novos testes de autorização para `shifts` (IDOR).
- Reforço de testes para import admin-only e rotas admin do frontend.
- Rodar regressão de login JWT, import CSV/XLSX, OCR e swaps.

---

## Arquivos que precisarão ser alterados

### Backend (prioridade alta)
1. `backend/utils/dependencies.py`
   - padronizar helper de admin efetivo.
2. `backend/api/shifts.py`
   - reforçar autorização por recurso (`/agent/{id}`, listas/export).
3. `backend/services/shift_service.py`
   - opcional: adicionar métodos com escopo por usuário/admin para reduzir lógica no router.
4. `backend/api/auth.py`
   - logs mínimos de autenticação e resposta consistente de papel.
5. `backend/utils/rate_limiter.py`
   - melhoria conservadora de identificação de IP sob proxy confiável.

### Frontend (prioridade média)
6. `frontend/src/pages/calendar_page.jsx`
7. `frontend/src/pages/shifts_page.jsx`
   - migrar consumo para rotas de “meu escopo” quando aplicável.
8. `frontend/src/contexts/auth_context.jsx`
   - manter cálculo de admin alinhado com backend (sem ampliar privilégios).
9. `frontend/src/router/app_router.jsx` e `frontend/src/components/app_layout.jsx`
   - manter/ajustar guardas e ocultação de UI por papel (sem alterar UX principal).

### Testes
10. `tests/test_routers.py`
11. `tests/test_api.py`
12. `tests/test_import.py`
13. `tests/test_rate_limit.py`
   - ampliar casos de autorização e não-regressão.

---

## Impacto esperado

### Ganhos
- Redução de risco de acesso indevido (IDOR).
- RBAC mais previsível e auditável.
- Garantia formal de import admin-only no backend (fonte de verdade).
- Base segura para, depois, incluir aba de preferências sem confundir permissões.

### Custo/impacto operacional
- Mudanças pequenas e localizadas em autorização.
- Sem necessidade de migração de banco ampla neste passo.
- Possível ajuste fino de frontend para endpoints de escopo próprio.

---

## Testes necessários (obrigatórios)

### Autorização backend
1. Médico não pode acessar `/shifts/agent/{outro_id}` → `403`.
2. Médico não pode usar endpoints globais definidos como admin-only (`/shifts` e exports, se endurecidos) → `403`.
3. Admin continua acessando tudo normalmente → `200`.

### Import admin-only
4. Médico em qualquer rota `/schedule-imports/*` → `403`.
5. Admin upload/validate/confirm/report permanece funcional.

### Auth/rate-limit
6. `/auth/login` mantém `429` após limite.
7. Login válido continua emitindo access+refresh sem regressão.

### Frontend/regressão
8. Rotas `/import`, `/swaps/pending`, `/admin/users` continuam inacessíveis para não-admin.
9. Calendário e Minha Escala de médico continuam funcionais após endurecimento.
10. Fluxo de swaps e OCR/import staging não quebra.

---

## Riscos de regressão

1. Frontend atual usa `/shifts/agent/{user.id}`; se política mudar abruptamente sem fallback, pode haver erro de carregamento.
2. Endpoints de export usados por usuários não-admin podem deixar de funcionar caso virem admin-only sem ajuste de UX.
3. Ajustes no helper de admin podem impactar usuários legados com `is_admin=true` e `role` divergente.

### Mitigação
- Implementar validações com feature flag leve (se necessário) para rollout gradual.
- Atualizar testes antes de endurecer regra.
- Fazer deploy em CT 102 com smoke test controlado.

---

## Ordem recomendada de implementação

1. **Testes primeiro (red/green de segurança)**
   - criar testes que capturem IDOR e regras admin-only esperadas.
2. **Padronização RBAC em `dependencies.py`**
   - helper único de decisão admin.
3. **Hardening de `backend/api/shifts.py`**
   - bloquear acesso cruzado por `agent_id`.
4. **Ajuste mínimo frontend (se necessário)**
   - usar endpoints no escopo próprio (`/me/shifts`) para médico.
5. **Logs mínimos de autenticação + ajuste rate-limit conservador**
6. **Rodada completa de regressão (auth/import/OCR/swaps/admin UI)**
7. **Deploy incremental no CT 102 + monitoramento CT 200**

---

## Plano de Execução da Fase 1 (commits pequenos e seguros)

### Commit 1 — testes de autorização de escopo
- adicionar testes para bloquear `/shifts/agent/{outro_id}` para médico.
- reforçar testes de import admin-only (todas as rotas críticas).

### Commit 2 — helper de RBAC central
- introduzir `is_effective_admin` em `dependencies.py`.
- ajustar `require_admin` para usar helper.

### Commit 3 — hardening do router de shifts
- aplicar checagem de ownership/admin em `/shifts/agent/{id}`.
- decidir e aplicar política explícita para `/shifts` e exports globais.

### Commit 4 — alinhamento frontend mínimo
- garantir que páginas de médico consumam rotas de escopo próprio.
- manter ocultação de UI por papel já existente.

### Commit 5 — observabilidade de auth/rate-limit
- logs estruturados para login sucesso/falha/429.
- melhoria conservadora da origem de IP sob proxy confiável.

### Commit 6 — regressão e documentação operacional
- atualizar docs (`docs/operations.md`/README backend) com matriz de permissões.
- executar suíte alvo de regressão e registrar evidências.

---

## Fora de escopo deste PASSO 1
- Implementação da aba de preferências de plantão.
- Mudanças amplas de schema de banco para novas features de negócio.
- Reescrita arquitetural de autenticação/autorização.


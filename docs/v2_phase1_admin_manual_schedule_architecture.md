# AgentEscala v2.0 — Fase 1 (PASSO 1 + endurecimento do importador admin)

Documento de planejamento conservador e incremental, baseado no código atual do repositório, com prioridade em segurança, RBAC, proteção de rotas e validação de upload.

## Diagnóstico atual

### Usuários, autenticação e permissões
- Modelo de usuário em `backend/models/models.py`:
  - `role` enum (`admin`, `medico`, `financeiro`, `agent` legado)
  - `is_admin` (flag booleana adicional)
  - `is_active`
- Autenticação JWT em `backend/api/auth.py`:
  - `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`
  - login aplica `rate_limit_login` (`backend/utils/rate_limiter.py`)
- Autorização administrativa central em `backend/utils/dependencies.py`:
  - `require_admin` aceita admin por `role == ADMIN` **ou** `is_admin == true`
  - há dualidade de fonte de verdade de privilégio (`role` x `is_admin`)

### Endpoints já admin-only (estado atual)
- Importação de escala (todos admin-only) — `backend/api/schedule_imports.py`:
  - `POST /schedule-imports/`
  - `POST /schedule-imports/{id}/validate`
  - `GET /schedule-imports/`
  - `GET /schedule-imports/{id}`
  - `GET /schedule-imports/{id}/summary`
  - `GET /schedule-imports/{id}/rows`
  - `POST /schedule-imports/{id}/confirm`
  - `GET /schedule-imports/{id}/report`
- Turnos admin-only (parcial) — `backend/api/shifts.py`:
  - `POST /shifts/`, `PATCH /shifts/{id}`, `DELETE /shifts/{id}`, `GET /shifts/consistency-report`
- Trocas admin-only (parcial) — `backend/api/swaps.py`:
  - `GET /swaps/pending`, `GET /swaps/export/excel`, `POST /swaps/{id}/approve`, `POST /swaps/{id}/reject`
- Gestão administrativa de usuários — `backend/api/users.py` (`/admin/users*`, `/admin/audit/users`)

### Como a importação está protegida hoje
- Backend: rotas de import usam `Depends(require_admin)` (proteção correta no servidor).
- Frontend: rota `/import` exige `ProtectedRoute requiredRole="admin"` (`frontend/src/router/app_router.jsx`) e o menu oculta link de import para não-admin (`frontend/src/components/app_layout.jsx`).

### Onde o importador aceita/tenta processar imagem/PDF hoje
- Backend (`backend/api/schedule_imports.py`) aceita content-type e extensões de:
  - CSV/XLSX **e também** PDF/imagens (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.tiff`).
- Frontend (`frontend/src/pages/import_page.jsx`) também anuncia e aceita seleção desses formatos em `accept` e textos da UI.
- Serviço (`backend/services/import_service.py`) ativa OCR para PDF/imagem:
  - tenta API OCR (`_read_ocr_via_api`)
  - fallback local para PDF (`_read_pdf_ocr` com `pypdf`)
  - fallback local para imagem (`_read_image_ocr` com `Pillow/pytesseract`)

### Onde nasce o erro técnico de OCR/Pillow/pytesseract
- Em `backend/services/import_service.py`, `_read_image_ocr()` lança:
  - `ValueError("OCR de imagem indisponível neste ambiente (dependências Pillow/pytesseract ausentes).")`
- Esse erro é reempacotado por `process_import_file()` em:
  - `ValueError("Não foi possível ler o arquivo '<nome>': <erro técnico>")`
- Em `backend/api/schedule_imports.py`, o `except ValueError` retorna HTTP 422 com `detail=str(exc)`.
- Resultado: o detalhe técnico interno vaza para o usuário final (falha de UX/escopo nesta fase).

### Como o frontend decide o que mostrar por usuário
- `AuthProvider` calcula `isAdmin` com `role === 'admin' || is_admin === true` (`frontend/src/contexts/auth_context.jsx`).
- Rotas admin (`/import`, `/swaps/pending`, `/admin/users`) ficam em guard específico (`frontend/src/router/app_router.jsx`).
- Menu lateral oculta itens admin para não-admin (`frontend/src/components/app_layout.jsx`).

### Inconsistências backend x frontend de permissões
- Frontend usa fluxo de “escopo próprio” para turnos do médico (via `user.id`), mas backend ainda permite endpoints amplos para autenticados em `shifts`.
- Conclusão: backend precisa reforçar escopo/autorização como fonte de verdade (não confiar só na ocultação de UI).

---

## Bug atual do importador

### Sintoma
Ao enviar `.jpeg` (ou outros arquivos de imagem/PDF sem dependências OCR locais disponíveis), o sistema retorna erro técnico citando indisponibilidade de OCR e dependências (`Pillow/pytesseract`).

### Causa técnica
1. Upload aceita imagem/PDF no endpoint admin de import.
2. Pipeline tenta OCR (API externa e fallback local).
3. Fallback local de imagem depende de libs não garantidas no ambiente.
4. Mensagem técnica da exceção é propagada para a resposta HTTP.

### Requisito para esta fase
- Escopo oficial do importador: **somente CSV e XLSX**.
- Rejeitar PDF/imagem com mensagem funcional e controlada (sem expor dependências internas).

---

## Riscos atuais

1. Ambiguidade de privilégio (`role` vs `is_admin`) gerando decisões inconsistentes de autorização.
2. Dependência de ocultação de UI sem endurecimento equivalente no backend em alguns fluxos.
3. Vazamento de detalhes internos de infraestrutura OCR no erro de upload.
4. Rate limit de login em memória local (não distribuído por réplica/proxy por padrão).
5. Revogação de refresh token em memória (`token_store`) volátil em restart.

---

## Plano por etapas (conservador e incremental)

### Etapa 1 — Consolidar RBAC sem quebrar compatibilidade
- Padronizar helper de decisão admin em `backend/utils/dependencies.py`:
  - `is_effective_admin(user)`
  - `require_admin` usa helper único
- Manter campos atuais (`role`, `is_admin`) na Fase 1, sem migração ampla de banco.

### Etapa 2 — Importação estritamente admin + validação estrita de arquivo
- Backend `schedule_imports`:
  - aceitar oficialmente apenas CSV/XLSX
  - remover aceitação de PDF/imagem no endpoint desta fase
  - retornar 415/422 com mensagem funcional: ex.
    - “Formato não suportado nesta fase. Envie CSV ou XLSX.”
- Serviço `import_service`:
  - não acionar OCR para uploads de import padrão nesta fase
  - evitar encadear mensagens técnicas de dependências para resposta do usuário
- Frontend `import_page`:
  - `accept` apenas `.csv,.xlsx,.xls`
  - atualizar textos de ajuda para remover referência a PDF/imagens

### Etapa 3 — Backend como fonte de verdade para autorização
- Revisar rotas de `shifts` com escopo por papel:
  - admin com visão ampla
  - médico limitado ao próprio escopo
- Evitar depender de guardas apenas no frontend.

### Etapa 4 — Hardening de autenticação e auditoria mínima
- Login rate-limit: manter solução atual (conservadora), com melhorias incrementais em telemetria e identificação de origem quando houver proxy confiável.
- Auditoria mínima:
  - manter `AdminUserAuditLog` para ações administrativas
  - adicionar logs estruturados de autenticação (sucesso, falha, bloqueio 429)

### Etapa 5 — Regressão orientada por testes
- Garantir não quebra de:
  - login JWT
  - swaps
  - calendário/minha escala
  - import CSV/XLSX com staging/confirm

---

## Arquivos que precisarão ser alterados

### Backend
1. `backend/utils/dependencies.py`
   - helper único de admin efetivo.
2. `backend/api/schedule_imports.py`
   - validação de content-type/extensão restrita a CSV/XLSX e mensagem amigável para formatos não suportados.
3. `backend/services/import_service.py`
   - não propagar erro técnico de OCR ao usuário no fluxo de import padrão desta fase.
4. `backend/api/shifts.py`
   - reforço de autorização por escopo (admin vs médico).
5. `backend/api/auth.py` e/ou camada de observabilidade
   - logs mínimos de autenticação.

### Frontend
6. `frontend/src/pages/import_page.jsx`
   - restringir `accept` e textos da UI para CSV/XLSX.
7. `frontend/src/router/app_router.jsx` e `frontend/src/components/app_layout.jsx`
   - manter/validar guardas admin de import.
8. `frontend/src/contexts/auth_context.jsx`
   - manter alinhamento de papel admin com backend.

### Testes
9. `tests/test_import.py`
   - validar rejeição amigável de PDF/JPG/JPEG/PNG para importador.
10. `tests/test_routers.py` / `tests/test_api.py`
   - autorização por escopo em rotas de turnos e import.
11. `tests/test_rate_limit.py`
   - garantir regressão zero no bloqueio de login (429).

---

## Impacto esperado

### Ganhos
- Segurança e previsibilidade maiores no controle de acesso.
- Importador com escopo claro (CSV/XLSX), UX mais limpa e sem vazamento técnico.
- Base preparada para futura aba de preferências, mantendo decisão final com admin.

### Impacto operacional
- Mudanças localizadas em validação e autorização.
- Sem reescrita arquitetural e sem migração ampla de banco na Fase 1.

---

## Testes necessários

### Autorização
1. Não-admin recebe `403` em todas as rotas administrativas de import.
2. Não-admin não acessa escopo de outro usuário em rotas de turnos após hardening.
3. Admin mantém acesso normal aos fluxos de gestão.

### Upload/validação de formato
4. Upload CSV válido continua funcionando.
5. Upload XLSX válido continua funcionando.
6. Upload PDF retorna erro funcional controlado (sem stack/detail técnico interno).
7. Upload JPG/JPEG/PNG retorna erro funcional controlado (sem menção a Pillow/pytesseract).

### Regressão
8. Login + refresh + logout sem regressão.
9. Calendário e “Minha Escala” continuam operando.
10. Swaps continuam operando.
11. Rate-limit de login mantém comportamento 429.

---

## Riscos de regressão

1. Frontend de import ainda aceitar formato antigo se não for alinhado com backend.
2. Endpoints de import podem quebrar clientes antigos que tentavam PDF/imagem.
3. Endurecimento de autorização em `shifts` pode impactar telas que dependam de visão ampla sem perfil admin.

### Mitigação
- Implementação em commits pequenos com testes por etapa.
- Mensagens de erro estáveis e funcionais.
- Deploy gradual com smoke tests no CT 102.

---

## Ordem recomendada de implementação

1. Testes de upload/autorizações (incluindo rejeição de PDF/imagem) — primeiro.
2. Restrição de upload no backend (`schedule_imports`) para CSV/XLSX.
3. Ajuste de mensagens funcionais e sanitização de erro no `import_service`.
4. Ajuste de UI do importador (accept + textos).
5. Hardening de autorização por escopo em `shifts`.
6. Ajustes finos de logs de autenticação e auditoria mínima.
7. Regressão completa e validação de deploy.

---

## Plano de Execução da Fase 1 (commits pequenos e seguros)

### Commit 1 — testes de base de segurança (já iniciado)
- Cobertura de admin-only em import e cenário de escopo de turnos (teste alvo de hardening).

### Commit 2 — importador admin estrito em CSV/XLSX
- Backend rejeita PDF/imagem com mensagem funcional controlada.
- Sem OCR no fluxo padrão desta fase.

### Commit 3 — frontend alinhado ao escopo oficial de upload
- `accept` e textos da página de import atualizados para CSV/XLSX.

### Commit 4 — hardening de autorização por escopo em turnos
- backend reforça ownership/admin no acesso por agente.

### Commit 5 — logs mínimos de autenticação + regressão
- observabilidade mínima de login e ações admin críticas.
- rodada de testes de regressão.

---

## Fora de escopo nesta fase
- Implementar a aba de preferências de plantão.
- Reativar OCR no importador padrão.
- Migrações amplas de banco sem necessidade de segurança imediata.

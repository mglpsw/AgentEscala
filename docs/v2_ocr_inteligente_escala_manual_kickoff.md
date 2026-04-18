# Kickoff proposto — OCR inteligente + edição manual de escala (AgentEscala v2)

## Objetivo
Iniciar implementação de forma incremental para:
1. importar PDF/imagem via API OCR externa (`api.ks-sk.net:9443`, via Agent Router),
2. classificar automaticamente linhas/colunas com match no formato canônico da base,
3. permitir validação/correção manual pelo admin das inconsistências,
4. memorizar padrões para melhorar acurácia,
5. combinar isso com edição manual administrativa da escala (admin vence conflito),
6. manter segurança e controle de acesso como prioridade.

> Observação técnica: hoje o projeto já usa `OCR_API_BASE_URL` e pipeline de `OcrImport`; esta proposta reaproveita essa base para reduzir risco.

---

## Estado atual relevante (reuso)

- Importação administrativa já existe com staging/confirm (`/schedule-imports/*`) e proteção `require_admin`.
- `import_service` já tem caminho OCR (API externa + fallback local) e já gera registro em `ocr_imports` quando o upload é OCR.
- Modelo `OcrImport` já possui:
  - `parsed_rows`, `errors`, `action_log`, status `draft/confirmed/discarded`.
- Existe área admin no frontend e fluxo de revisão de staging.

Isso permite iniciar sem reescrever arquitetura.

---

## Arquitetura funcional alvo (incremental)

## 1) Pipeline OCR por fases

### Fase A — OCR remoto obrigatório para PDF/Imagem
- Para arquivos `.pdf/.png/.jpg/.jpeg/.webp/.tiff`, backend envia arquivo para `api.ks-sk.net:9443`.
- Agent Router retorna texto estruturado (ou texto bruto + metadados).
- Desabilitar fallback local para produção desta trilha (evita erro de dependência local).
- Se OCR remoto falhar, retornar erro funcional controlado ao admin (sem stack técnico).

### Fase B — Parsing canônico + matching automático
- Transformar OCR em linhas canônicas:
  - `profissional`, `data`, `hora_inicio`, `hora_fim`, `observacoes/origem`.
- Rodar matching com usuários/plantões existentes:
  - match por `user_id` quando disponível,
  - match por nome normalizado/fuzzy,
  - classificação: `matched`, `ambiguous`, `unmatched`, `invalid`.
- Gerar score de confiança por linha.

### Fase C — Validação manual pelo admin
- Admin revisa linhas `ambiguous/unmatched/invalid` antes de confirmar.
- Cada correção gera trilha em `action_log` (já existente no `OcrImport`).
- Confirmar import cria `Shift` automaticamente para linhas resolvidas.

---

## 2) Memória de padrões (aprendizado incremental)

### Necessidade
Quando IA não conseguir encaixar padrão da imagem/PDF no esquema da base, permitir:
- admin mapear padrão para classe existente,
- ou cadastrar padrão novo.

### Regras de permissão
- Admin comum: pode mapear padrão para classe existente.
- **Somente superadmin `mf.soares@ks-sm.net`**: pode criar nova classe/campo canônico.

### Proposta de modelagem mínima
Adicionar tabelas novas (sem quebrar legado):

1. `ocr_pattern_classes`
- `id`, `name`, `description`, `is_active`, `created_by`, `created_at`
- Ex.: `plantao_noturno_legacy`, `coluna_medico_abreviado`.

2. `ocr_pattern_memory`
- `id`, `pattern_hash`, `raw_pattern`, `class_id`, `mapped_field`
- `confidence`, `times_used`, `last_used_at`
- `created_by`, `updated_by`

3. `superadmin_allowlist` (opcional) **ou** regra via config/env
- nesta fase, mais simples: env `SUPERADMIN_EMAILS=mf.soares@ks-sm.net`.

### Uso no runtime
- Antes do parsing final, consultar memória por `pattern_hash`/similaridade.
- Aplicar sugestão automática com score.
- Se admin corrigir manualmente, atualizar memória (`times_used++`).

---

## 3) Edição manual de escala (junto com OCR)

Para convergir com a proposta anterior de escala manual:
- Admin cria/edita/exclui/sobrescreve plantões.
- Sobrescrita administrativa prevalece em conflito.
- Turnos oficiais (templates) continuam sendo base da aplicação.

### Integração com OCR
- OCR confirmada gera shifts com `source=ocr`.
- Se admin ajustar manualmente, gerar `source=manual_admin` + marca de override.
- Calendário final do médico exibe estado consolidado (sem pedir aceite do médico).

---

## Plano de início (sequência segura)

## Etapa 0 — Guardrails (primeiro)
1. Manter import CSV/XLSX estável.
2. Introduzir feature flags:
   - `FEATURE_OCR_REMOTE_IMPORT`
   - `FEATURE_OCR_PATTERN_MEMORY`
   - `FEATURE_MANUAL_SCHEDULE_OVERRIDE`
3. Logs estruturados de autenticação e ações admin de import/edição.

## Etapa 1 — OCR remoto controlado
1. Padronizar client OCR para `api.ks-sk.net:9443` via config.
2. Uniformizar contrato de resposta OCR (adapter no backend).
3. Erros funcionais padronizados para falha OCR.
4. Testes de integração mockando Agent Router.

## Etapa 2 — Matching automático + staging OCR
1. Adicionar classificação (`matched/ambiguous/unmatched`).
2. Expor endpoint admin para revisar/corrigir linhas OCR.
3. Confirmar apenas linhas válidas/resolvidas.

## Etapa 3 — Memória de padrões
1. Criar tabelas de classe/memória.
2. Aplicar sugestões automáticas em nova importação.
3. Permissão de criar nova classe/campo restrita ao superadmin.

## Etapa 4 — Edição manual de escala integrada
1. CRUD/admin override de plantões.
2. Precedência `manual_admin` sobre `ocr/import/swap`.
3. Ajuste de leitura do calendário para mostrar estado final consolidado.

---

## API proposta (inicial)

### OCR/admin
- `POST /admin/ocr/import` (upload PDF/imagem)
- `GET /admin/ocr/imports/{id}` (detalhe + linhas + score)
- `PATCH /admin/ocr/imports/{id}/rows/{row_id}` (correção manual)
- `POST /admin/ocr/imports/{id}/confirm`
- `POST /admin/ocr/imports/{id}/discard`

### Memória de padrões
- `GET /admin/ocr/pattern-classes`
- `POST /admin/ocr/pattern-classes` (**superadmin only**)
- `POST /admin/ocr/pattern-memory/map`

### Escala manual
- `POST /admin/manual-shifts`
- `PUT /admin/manual-shifts/{id}`
- `DELETE /admin/manual-shifts/{id}`
- `POST /admin/manual-shifts/override`

---

## Segurança e autorização

1. Backend é fonte de verdade:
- todos endpoints acima com `require_admin`.
- criação de classe/campo OCR protegida por check de superadmin.

2. Frontend:
- ocultar UI por papel, mas sem confiar nisso para segurança.

3. Auditoria mínima obrigatória:
- login sucesso/falha/429.
- import OCR criada/confirmada/descartada.
- correção manual de linha OCR.
- override manual de escala.

---

## Testes obrigatórios para iniciar

1. Autorização
- não-admin recebe 403 em OCR/admin endpoints.
- admin recebe 200/201 no fluxo completo.
- admin comum recebe 403 ao criar classe/campo; superadmin permitido.

2. OCR pipeline
- PDF/imagem -> chamada ao client OCR remoto.
- fallback técnico interno não vaza para resposta.
- classificação automática gera status e score por linha.

3. Memória
- padrão novo mapeado -> reutilizado em import seguinte.
- atualização de `times_used` e rastreio de autor.

4. Escala manual
- admin override prevalece sobre shift OCR/import pré-existente.
- médico visualiza escala final consolidada.

---

## Plano de execução em commits pequenos

### Commit A
- Infra de feature flags + adapter OCR remoto + testes de contrato (mock).

### Commit B
- Endpoints OCR admin (`import/detail/confirm/discard`) com staging em `OcrImport`.

### Commit C
- Classificação automática + tela admin de revisão de inconsistências.

### Commit D
- Memória de padrões (classes + mapeamento) com permissão superadmin.

### Commit E
- Edição manual de escala + override administrativo integrado ao calendário final.

### Commit F
- Regressão completa (auth/import/swaps/calendário) e rollout controlado CT 102.

---

## Recomendação prática para começar agora

Se você aprovar, a primeira entrega técnica que eu faria seria:
1. **Commit A** (adapter OCR remoto + erro funcional sem leak técnico + flags),
2. em seguida **Commit B** (endpoints admin OCR com `OcrImport`),
3. depois avançar para memória e manual override.

Assim evoluímos rápido, mas sem quebrar o que já está funcionando.

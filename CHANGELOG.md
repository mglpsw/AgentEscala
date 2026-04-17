# Changelog

## [1.5.2] - 2026-04-17

### Corrigido
- compatibilidade de login público adicionada para `/api/auth/login` (além de `/auth/login`), evitando bloqueio indevido em ambientes com proxy/prefixo `/api`.
- rotas existentes continuam protegidas por JWT (`401/403`) sem abrir endpoints administrativos.

### Adicionado
- endpoint administrativo `PATCH /admin/users/{id}/status` para ativar/desativar usuários com validação de segurança (sem auto-desativação do admin autenticado).
- ajuste de controle de acesso no frontend para considerar também `is_admin`, além de `role=admin`.

### Testes
- cobertura para login público em `/api/auth/login`.
- cobertura para patch de status administrativo e validação de `403` para usuário não-admin.

## [1.5.1] - 2026-04-17

### Consolidado (operação segura OCR)
- instrumentação Prometheus adicionada para OCR com métricas dedicadas: `ocr_requests_total`, `ocr_api_success_total`, `ocr_api_failure_total`, `ocr_fallback_used_total` e `ocr_api_latency_seconds`.
- logs operacionais OCR padronizados com estratégia (`api`/`fallback_local`), status (sucesso/falha), latência da API externa e motivo resumido do fallback.
- endpoint `/api/v1/info` mantém contrato existente e passa a expor também `api_timeout_seconds` e `api_verify_ssl` no bloco `ocr`.
- smoke test operacional pós-deploy adicionado em `scripts/smoke_ocr_release.sh` (health, info, metrics e checklist manual para fallback).
- documentação operacional curta em PT-BR adicionada: `docs/ocr_operacao_pos_deploy.md`.
- testes dedicados de `/api/v1/info` e validação de presença de métricas OCR no `/metrics`.

### Alterado
- usuário administrativo principal `mf.soares@ks-sm.net` passa a exigir configuração explícita de senha por variável de ambiente (`AGENTESCALA_PRIMARY_ADMIN_PASSWORD`), com placeholder seguro no código (`CHANGE_ME`) para evitar credencial versionada.
- versão da aplicação atualizada para `1.5.1` (`VERSION` e `APP_VERSION`).
- integração OCR revisada para priorizar a API `https://api.ks-sm.net:9443`, com fallback seguro para o parser/calibração local do último merge.
- endpoint `/api/v1/info` passa a expor status/configuração de integração OCR para observabilidade operacional.
- versão do frontend alinhada para `1.5.1`.
- endpoint `/health` consolidado com status resumido de OCR (`enabled`/`disabled`) sem exposição de segredos.
- novas variáveis OCR documentadas e consolidadas: `OCR_API_BASE_URL`, `OCR_API_TIMEOUT_SECONDS`, `OCR_API_ENABLED`, `OCR_API_VERIFY_SSL`.
- revisão operacional da `main` com log de startup orientado a diagnóstico da integração OCR.

### Testes
- reforço de cobertura para OCR: payload aninhado e leitura via API mockada.
- validação de `/health` com versão, banco e estado OCR.

## [1.5.0] - 2026-04-17 — Release estável pré-OCR

### Adicionado
- documentação completa em PT-BR (`README.md`, `ARCHITECTURE.md`, `CONTEXT.md`).
- preparação da estrutura OCR em `backend/services/ocr/` (base isolada, sem integração ativa).
- arquivo `VERSION` com versão formal `1.5.0`.

### Melhorado
- endpoint `/health` com versão e status do banco (`up`/`down`).
- padronização de logs e consolidação de observabilidade em módulo dedicado.
- novas métricas Prometheus seguras: `agentescala_total_shifts`, `agentescala_total_swaps`, `agentescala_imports_success_total`, `agentescala_imports_failure_total`.

### Observações
- sistema considerado estável para expansão incremental.
- base OCR criada sem alterar comportamento atual do fluxo de importação.

## [1.4.0] - 2026-04-16

### Adicionado
- OCR integrado ao fluxo de importação administrativa com suporte a PDF e imagens, sempre enviando para staging.
- revalidação explícita do staging via `POST /schedule-imports/{import_id}/validate`.

### Alterado
- pipeline de importação passou a aplicar validação centralizada também no staging.

## [1.3.0] - 2026-04-16

### Adicionado
- validação de conflitos de plantão antes de gravação via API e confirmação de importação.
- endpoint administrativo `POST /admin/schedule/validate` para preview sem persistência.

## [1.2.0] - 2026-04-16

### Adicionado
- vínculo incremental de plantões com usuário via `shifts.user_id`.
- endpoints `GET /me`, `GET /me/shifts` e exportação de escala individual.

## [1.1.0] - 2026-04-16

### Adicionado
- login/logout JWT e perfis de acesso.
- CRUD administrativo de usuários.

## [1.0.0] - 2026-04-14

### Adicionado
- base estável inicial com auth, plantões, trocas, importação CSV/XLSX e frontend React.

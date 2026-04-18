# Changelog

## [1.6.1] - 2026-04-18

### Adicionado
- Fase 1: recorrência semanal admin para plantões com preview obrigatório e confirmação em lote via `/admin/recurring-shifts`.
- suporte backend para batch/auditoria de recorrência (`recurring_shift_batches` e `recurring_shift_batch_items`) com rastreio de conflitos, duplicatas, itens criados e itens pulados.
- validação de limite de horizonte futuro em até 6 meses na geração da recorrência semanal.
- UI no painel Admin de Plantões para criar recorrência semanal, visualizar preview e confirmar lote.
- testes backend cobrindo geração, limite de 6 meses, noturno cruzando dia, duplicata/conflito e regressão de compatibilidade com camada documental `/admin/imports`.
- confirmação granular por item no batch de recorrência (`item_decisions` com `create|skip|keep_existing`), com auditoria de decisão por item.
- endpoint de detalhe de batch de recorrência enriquecido com parâmetros do lote, resumo, itens, decisões e shifts criados.

## [1.6.0] - 2026-04-18

### Adicionado
- nova camada documental admin-only em `/admin/imports` com parsing incremental para XLSX multiaba e payload OCR estruturado, sem bypass de staging/revisão.
- formato canônico interno normalizado em serviço dedicado para consolidação de cabeçalhos variantes, detecção de mês/ano, normalização de nomes com ruído e interpretação de turno noturno.
- fluxo adicional parse → normalized-preview → apply-to-staging → confirm, reaproveitando o pipeline legado `/schedule-imports`.
- endpoint assistido para criação de usuários candidatos (`POST /admin/imports/{id}/create-missing-users`) com trilha de ação no documento.
- UI mínima de debug OCR na página de importação para colar payload JSON e enviar ao staging de forma conservadora.
- testes de fase 5 para normalização semântica e fluxo dos novos endpoints.

### Compatibilidade
- contratos existentes da importação CSV/XLSX não foram removidos nem alterados; a nova camada estende o comportamento já validado.

## [1.5.5] - 2026-04-17

### Alterado
- documentação de deploy homelab atualizada para a arquitetura canônica do CT 102:
  `/opt/repos/AgentEscala`, stack `agentescala_official`, backend em
  `192.168.3.155:18000` e NPM interno em `443`.
- README, guia de deploy, guia operacional e backup/restore agora documentam que
  `https://escala.ks-sm.net:9443` é a origem externa via roteador, enquanto
  dentro do CT 102 o NPM escuta em `443`.
- `infra/.env.homelab.example` passa a refletir os nomes e URLs canônicos do
  deploy validado: `escala.ks-sm.net`, `VITE_API_BASE_URL` com `:9443`, volume
  `agentescala_postgres_data_official18000` e stack `agentescala_official`.
- `infra/docker-compose.homelab.yml` passa a usar `VITE_API_BASE_URL` vindo do
  env, removendo hardcode para `api.ks-sm.net:9443`.
- `infra/scripts/plan_npm_publish.sh` atualizado para orientar NPM com upstream
  `192.168.3.155:18000` e lembrar que `9443` é port-forward externo.

### Planejado
- plano de limpeza CT 102 adicionado em `docs/ct102_cleanup_plan.md`, sem
  executar remoções. O plano lista diretórios, containers, redes e volumes
  legados a excluir/mover em uma janela futura.

## [1.5.4] - 2026-04-17

### Adicionado
- filtros opcionais `action` e `target_user_id` no endpoint admin-only `GET /admin/audit/users`, mantendo total compatibilidade de contrato.
- cobertura de testes para filtros de auditoria por ação, por usuário-alvo, paginação e restrição admin-only.
- template versionado `infra/.env.homelab.example` com variáveis obrigatórias do deploy CT 102.

### Alterado
- `infra/docker-compose.homelab.yml` agora usa caminhos relativos e portáveis (sem hardcode de `/root/AgentEscala`), reduzindo falhas de bootstrap em novos hosts.
- serviço `backend` no compose homelab passa a declarar `image` + `build` de forma explícita para fluxo previsível de build/tag.
- script `infra/scripts/couple_to_homelab.sh` passou a detectar automaticamente `docker compose` ou `docker-compose`.
- README e CONTEXT atualizados com instrução oficial de deploy, validações mínimas e arquitetura real do stack.

### Limpeza (sem remoção destrutiva)
- arquivos antigos/confusos movidos para `infra/legacy/`:
  - `docker-compose.homelab.yml.bak`
  - `COMMIT_MSG_fallback_spa_nginx.txt`
  - `COMMIT_MSG_nginx_9443_spa.txt`

## [1.5.3] - 2026-04-17

### Adicionado
- trilha mínima de auditoria administrativa de usuários com nova tabela `admin_user_audit_logs` (ação, admin responsável, usuário alvo, resumo e timestamp).
- endpoint admin-only `GET /admin/audit/users` para consulta de eventos recentes com `skip`/`limit` básico.

### Alterado
- endpoints administrativos de usuários agora registram auditoria em criação, edição, ativação/desativação e exclusão.
- sanitização de payload de auditoria para não persistir senha em claro nem hash de senha (`password_changed=true` quando aplicável).

### Testes
- cobertura para geração de log em criação/edição e ativação/desativação de usuário.
- cobertura para bloqueio de acesso de não-admin ao endpoint de auditoria.

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

### Frontend (hardening admin)
- rota administrativa no frontend agora redireciona usuário autenticado sem privilégio para `/calendar`, evitando exposição da tela administrativa por URL direta.
- navegação admin permanece visível somente para usuários com `role=admin` ou `is_admin=true`.
- suíte de testes frontend ampliada com cenários de autorização admin (visibilidade de menu, bloqueio/redirecionamento por URL, renderização de página admin e não regressão do fluxo de login).

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

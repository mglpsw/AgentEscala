# Changelog

## [1.0.0] - 2026-04-14 — Release 01

### Features entregues

- Autenticação JWT completa: login, refresh token automático e logout
- Calendário real do médico com FullCalendar (mensal/semanal, locale pt-BR)
- Lista de turnos com filtros por data e texto (tabela paginável)
- Trocas de plantão: solicitação, listagem e cancelamento pelo médico
- Painel admin de trocas pendentes: aprovação e rejeição com notas
- UI de importação de escala: upload CSV/XLSX, revisão do staging linha a linha e confirmação criando turnos reais
- Frontend React/Vite/Tailwind servido via FastAPI StaticFiles com fallback SPA
- Pipeline de importação com staging, detecção de duplicatas e overlaps, confirmação atômica
- Endpoint `/health` com status, timestamp e versão
- Endpoint `/metrics` com métricas Prometheus (configurável por env)
- 70 testes automatizados cobrindo auth, users, shifts, swaps e importação

### Limitações conhecidas

- Importação suporta apenas CSV e XLSX; PDF e OCR não estão no escopo desta versão
- Revogação de refresh tokens é in-memory (limpa ao reiniciar o servidor)
- Sem rate limiting no endpoint de login
- Sem testes de frontend automatizados (E2E)
- Operações administrativas limitadas: criação/gestão de usuários pela UI não está funcionando
- Edição manual da escala e inclusão de plantões via frontend não estão operacionais
- Importação de XLSX é sensível ao formato: arquivos que não seguem o template podem falhar; recomenda-se CSV ou usar o template fornecido

---

## [1.2.0] - 2026-04-14

### Adicionado
- Página /swaps implementada no frontend React:
	- Listagem real de trocas do usuário logado
	- Formulário funcional para solicitar nova troca
	- Cancelamento de solicitações pendentes
	- Estados de loading, erro e vazio
	- Integração direta com backend FastAPI
	- Componentes auxiliares: SwapCard, SwapForm
- Nenhuma dependência com a etapa E7
- Build e validação manual realizados com sucesso

### Corrigido
- Ajustes menores de documentação e validação de build

### Observações
- Não houve conflito com E7
- Não houve alteração em backend, Docker ou contratos de API
Este arquivo registra apenas mudanças relevantes para uso real do AgentEscala.

Objetivo:
- manter histórico legível
- evitar burocracia excessiva
- facilitar operação no CT 102 e futuras atualizações

## Regras de manutenção

Comece do jeito mais simples possível.

Use SemVer:
- `MAJOR.MINOR.PATCH`
- `PATCH`: correção sem mudar o comportamento esperado
- `MINOR`: nova funcionalidade compatível com o uso anterior
- `MAJOR`: mudança que quebra compatibilidade

Política prática deste repositório:
- toda mudança relevante em script operacional atualiza este arquivo
- toda entrega estável deve resultar em tag Git no formato `vX.Y.Z`
- toda feature nova sobe `MINOR`
- toda correção sobe `PATCH`
- toda quebra de compatibilidade sobe `MAJOR`

Padrão de commits recomendado:
- `feat:` nova funcionalidade compatível
- `fix:` correção de bug
- `docs:` documentação
- `chore:` manutenção sem impacto funcional direto
- `refactor:` simplificação interna sem mudança de comportamento esperada

Fluxo recomendado:
- branch
- commits consistentes
- atualização deste `CHANGELOG.md`
- PR
- merge na `main`
- tag Git
- release

Escopo de versionamento formal:
- scripts operacionais e automações reais devem seguir este processo
- scripts auxiliares, testes pontuais e experimentos não precisam de release formal

Versão recomendada para esta rodada operacional:
- `0.2.0`

Tag recomendada após merge:
- `v0.2.0`

Mensagem de tag sugerida:
- `Deploy operacional mínimo no CT 102`

## [0.2.0] - 2026-04-13

### Added
- suporte a backup e restore básico do PostgreSQL do AgentEscala
- endpoint `/metrics` com métricas mínimas de operação
- helper seguro para planejamento de publicação via Nginx Proxy Manager
- exemplo de scrape Prometheus do lado do projeto
- runbook operacional curto para o CT 102

### Changed
- deploy homelab endurecido para CT 102 com isolamento por compose, rede e volume
- bind do backend preparado para uso seguro atrás do NPM
- documentação operacional alinhada com validação real e rollback simples

### Fixed
- validação de conflito de porta antes do deploy
- suporte a `ENV_FILE` externo no script de deploy para validações isoladas
- healthcheck do backend mais confiável no stack homelab

## [0.1.0] - 2026-04-13

### Added
- primeira base operacional do AgentEscala com compose próprio
- migrações automáticas antes do backend subir
- seed e validação HTTP fim a fim do backend

### Changed
- backend endurecido com autenticação mínima por JWT nos endpoints sensíveis

### Fixed
- rotas de exportação priorizadas corretamente
- ajustes de runtime para execução consistente em host Docker compartilhado
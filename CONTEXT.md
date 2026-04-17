# CONTEXT — AgentEscala (para agentes IA)

## Estado atual (release 1.5.3)

AgentEscala está estável em operação com:

- backend FastAPI;
- frontend React/Vite;
- autenticação JWT;
- importação com staging e validação;
- observabilidade via `/health`, `/metrics` e `/api/v1/info`;
- OCR integrado ao fluxo de importação para PDF/imagem.
- auditoria administrativa mínima para gestão de usuários (persistência + consulta admin-only).

## Atualização operacional (2026-04-17)

- trilha de auditoria administrativa de usuários ativa para criação, edição, ativação/desativação e exclusão via endpoints administrativos.
- endpoint `GET /admin/audit/users` disponível para consulta de eventos recentes de auditoria (admin-only).
- endpoint de login permanece público e compatível em dois caminhos: `/auth/login` e `/api/auth/login`.
- área administrativa de usuários reforçada com endpoint dedicado de status (`PATCH /admin/users/{id}/status`), protegido por dependência admin no backend.
- frontend passou a considerar `role=admin` **ou** `is_admin=true` para renderização/guarda de rotas administrativas.

## OCR em produção (como funciona hoje)

- Prioriza a API externa `https://api.ks-sm.net:9443`.
- Aceita payloads OCR em formatos diversos (`raw_text`, `text`, `content`, `lines`, `data`, `result`).
- Mantém fallback local calibrado para continuidade operacional.
- Registra estratégia `ks-sm-api-ocr` quando o OCR externo é aplicado.
- Não altera comportamento de CSV/XLSX.

## Decisões consolidadas

- Estabilidade > refatoração estética.
- Fluxo de staging permanece obrigatório antes da confirmação.
- Fallback OCR local não pode ser removido.
- Variáveis OCR ficam centralizadas em `settings`.
- Logs e observabilidade devem ser úteis e objetivos.

## Limitações atuais

- Qualidade OCR depende da qualidade do arquivo de entrada.
- Diferenças de payload entre provedores OCR exigem manutenção de compatibilidade.
- Automação de decisão de escala permanece assistida (sem bypass administrativo).

## Próximos passos realistas

1. Melhorar calibração OCR com base em amostras reais.
2. Aumentar cobertura de testes de fallback e payloads não usuais.
3. Evoluir notificações operacionais (ex.: Telegram) com ativação gradual.

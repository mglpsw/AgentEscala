# CONTEXT — AgentEscala (para agentes IA)

## Estado atual (release 1.5.1)

AgentEscala está estável em operação com:

- backend FastAPI;
- frontend React/Vite;
- autenticação JWT;
- importação com staging e validação;
- observabilidade via `/health`, `/metrics` e `/api/v1/info`;
- OCR integrado ao fluxo de importação para PDF/imagem.

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

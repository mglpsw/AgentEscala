# Diagnóstico de conexão (main vs versões estáveis anteriores)

Data da verificação: 2026-04-18 (UTC)

## Escopo verificado

- Commit atual: `6905ae3` (work)
- Ajuste imediatamente anterior: `8cc152f`
- Referência estável usada como base de comportamento: configuração documentada de desenvolvimento local em `:8000` (backend README, docker-compose e `.env.example`).

## Erros de conexão identificados

### 1) Frontend (dev) x Proxy Vite x Backend: porta padrão divergente

**Sintoma**
- Em desenvolvimento, o cliente Axios usa `/api` (proxy do Vite).
- Quando `VITE_API_BASE_URL` não está definida, o Vite estava apontando para `http://127.0.0.1:8020`, enquanto backend local/documentação usam `8000`.
- Resultado esperado em ambiente padrão: falhas 502/ECONNREFUSED no proxy para chamadas de API.

**Causa raiz**
- Fallback inconsistente de porta no `vite.config.js`.

**Correção aplicada**
- Ajustado fallback do proxy Vite para `http://127.0.0.1:8000`, alinhando com backend local e documentação.

### 2) Frontend ↔ Backend sob reverse proxy: rota canônica de `shift-requests`

**Sintoma histórico (já corrigido antes desta verificação)**
- A listagem de solicitações usava `/shift-requests` (sem barra final), gerando redirect 307 de FastAPI para `/shift-requests/`.
- Em alguns proxies/homelab esse redirect causava erro intermitente de fetch/autenticação.

**Estado atual**
- A chamada já está no formato canônico `/shift-requests/`, reduzindo risco de quebra por redirect.

### 3) Backend e compatibilidade de prefixo `/api`

**Validação**
- O backend registra routers tanto sem prefixo quanto com `/api`, mantendo compatibilidade entre acesso direto e acesso via proxy.
- Esse ponto está consistente no estado atual.

## Conclusão

- **Erro ativo encontrado e corrigido nesta entrega:** fallback de porta do proxy Vite (`8020` → `8000`).
- **Erro de rota de conexão observado nas últimas mudanças:** já havia sido corrigido no último commit para `shift-requests` canônico.
- **Proxy backend `/api`:** configuração atual está consistente com o padrão estável.

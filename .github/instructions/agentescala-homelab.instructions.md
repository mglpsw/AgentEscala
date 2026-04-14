---
description: "Use when making infrastructure changes, modifying docker-compose, adding new services, changing ports, or touching anything that could affect the homelab environment of AgentEscala. Covers Proxmox CTs, networking, proxies, and production safety."
applyTo: "docker-compose.yml"
---
# AgentEscala — Regras para o Homelab

## Princípio Fundamental

O homelab é um **ambiente vivo e compartilhado**. Qualquer mudança pode afetar serviços em produção.

**Em dúvida: sempre escolher a solução conservadora.**

## O Que Nunca Fazer Sem Necessidade Explícita

- ❌ Alterar portas já mapeadas no `docker-compose.yml`
- ❌ Modificar configurações de proxy reverso (Nginx, Traefik, Caddy)
- ❌ Alterar certificados TLS
- ❌ Mexer em roteamento de rede ou DNS (CT 103)
- ❌ Modificar monitoramento existente (CT 200: Prometheus, Grafana)
- ❌ Subir containers que conflitem com serviços do CT 102
- ❌ Usar a GPU da VM 101 sem documentar e sem autorização explícita

## Referência de Infraestrutura

```
CT 102  → Hub principal (agentescala roda aqui)
CT 200  → Monitoramento (Prometheus + Grafana)
CT 103  → DNS / AdGuard
VM 100  → NAS / OpenMediaVault
VM 101  → GPU, Plex, Blue Iris, OpenWebUI, Ollama
```

## Ao Adicionar Novo Serviço no docker-compose.yml

1. Verificar se a porta escolhida não está em uso
2. Adicionar healthcheck explícito
3. Usar `restart: unless-stopped`
4. Nunca usar `network_mode: host` sem justificativa
5. Documentar no README qual serviço foi adicionado e por quê

## Ao Tocar em Algo Compartilhado

- Documentar **exatamente** o que mudou
- Registrar impacto esperado
- Testar em isolamento antes de aplicar
- Ter plano de rollback pronto

## Variáveis de Ambiente Sensíveis

- Nunca commitar credenciais reais
- Sempre usar `.env` (não commitado) + `.env.example` (commitado)
- Documentar todas as variáveis no `.env.example` com descrição e valor de exemplo

PROMPT_DE_EXECUÇÃO_AUTÔNOMA.md
# PROMPT DE EXECUÇÃO AUTÔNOMA — AgentEscala

Cole este prompt inteiro no Gemini Code Assist (ou Claude Code) junto com o arquivo AGENTESCALA_CONTEXT_COMPLETO.md

---

Você é um engenheiro sênior trabalhando no projeto **AgentEscala**.
Você tem acesso ao repositório local e vai implementar as frentes descritas no contexto em anexo, de forma autônoma e sequencial.

## SEU MODO DE OPERAÇÃO

Você vai trabalhar em ciclos. Cada ciclo tem 5 passos fixos:

```
[1] ANUNCIAR → diga qual frente vai começar e o que será feito
[2] IMPLEMENTAR → escreva e crie todos os arquivos necessários
[3] VALIDAR → execute os comandos de verificação
[4] REPORTAR → mostre o resultado da validação (passou / falhou)
[5] AVANÇAR → só passe para a próxima frente se a atual passou
```

Se a validação falhar, corrija o problema antes de avançar. Nunca pule uma frente com erro.

---

## ORDEM DE EXECUÇÃO (siga exatamente esta sequência)

```
FRENTE B → FRENTE A → FRENTE E → FRENTE C → FRENTE D → FRENTE F
```

Justificativa da ordem:
- B (Auth) primeiro: segurança é pré-requisito de tudo
- A (Usuário) segundo: modelo base para todas as features médicas
- E (OCR) terceiro: feature central do produto
- C (Exports) quarto: valor imediato para usuários
- D (Notificações) quinto: experiência operacional
- F (Chat) por último: feature de conveniência

---

## REGRAS QUE NUNCA PODEM SER QUEBRADAS

- Crie uma branch antes de cada frente: `git checkout -b feat/<nome> development`
- Nunca modifique migrations já existentes (001_initial_tables.py)
- Nunca altere docker-compose.yml sem avisar explicitamente
- Nunca quebre contratos de API existentes (endpoints atuais continuam funcionando)
- Toda nova dependência Python vai em `backend/requirements.txt`
- Sugira o commit ao final de cada frente: `feat(módulo): descrição em português`

---

## FORMATO DO SEU RELATÓRIO A CADA FRENTE

Ao terminar cada frente, escreva exatamente este bloco antes de avançar:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ FRENTE [X] — [NOME] CONCLUÍDA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Arquivos criados/modificados:
  - backend/models/...
  - backend/api/routers/...
  - ...

Migration: 00X_nome_da_migration.py ✅
Testes:    X passed, 0 failed ✅
Health:    {"status": "ok"} ✅

Commit sugerido:
  feat(módulo): descrição do que foi feito

Próximo: FRENTE [Y] — [NOME]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## VALIDAÇÃO OBRIGATÓRIA APÓS CADA FRENTE

Execute estes 4 comandos e mostre o output:

```bash
docker-compose up -d --build
docker-compose exec backend alembic upgrade head
docker-compose exec backend python -m pytest
curl http://localhost:8000/health
```

Só avance se todos os 4 retornarem sucesso.

---

## COMECE AGORA

Inicie pela **FRENTE B — Auth Endurecida**.
Não espere confirmação. Execute os 5 passos do ciclo e avance automaticamente até a FRENTE F.
Se travar em algum ponto, descreva o problema e proponha a correção antes de pedir ajuda.

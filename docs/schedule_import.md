# Importação de Escala Base

Esta funcionalidade permite importar a escala do mês anterior via arquivo tabular (CSV ou XLSX), normalizando os turnos e detectando inconsistências antes da criação efetiva dos registros.

## Fluxo

```
Upload arquivo  →  Staging (ScheduleImportRow)  →  Revisão  →  Confirmação  →  Shifts reais
```

1. Admin faz upload do arquivo via `POST /schedule-imports/`
2. O sistema parseia, normaliza e valida cada linha, persistindo no staging
3. Admin revisa o resumo (`GET /schedule-imports/{id}/summary`) e inconsistências (`GET /schedule-imports/{id}/rows?row_status=warning`)
4. Se satisfeito, confirma a importação: `POST /schedule-imports/{id}/confirm`
5. Linhas válidas/warning com profissional resolvido viram `Shift` reais
6. Download do relatório de inconsistências: `GET /schedule-imports/{id}/report`

## Formato do Arquivo

### CSV

- Separadores aceitos: `,` e `;` (detectado automaticamente)
- Encoding: UTF-8 ou UTF-8-BOM
- Primeira linha: cabeçalho com nomes de colunas (case-insensitive)

### Excel (.xlsx)

- Primeira linha: cabeçalho
- Primeira aba (`ws.active`)
- Campos de hora podem ser `time` objects nativos do Excel

### Colunas Esperadas

| Campo canônico | Aliases aceitos | Obrigatório |
|----------------|-----------------|-------------|
| `profissional` | professional, nome, agente, colaborador | ✅ |
| `data` | date, data_turno, shift_date | ✅ |
| `hora_inicio` | start_time, inicio, start_hour | ✅ |
| `hora_fim` | end_time, fim, end_hour | ✅ |
| `total_horas` | horas, hours, duration, duracao | ❌ |
| `observacoes` | obs, notes, observations | ❌ |
| `origem` | source, fonte | ❌ |
| `dia_semana` | dia, day, weekday | ❌ (aceito, ignorado) |

### Formatos de Data

- `DD/MM/YYYY` (padrão BR) — recomendado
- `YYYY-MM-DD`
- `DD-MM-YYYY`
- Número serial do Excel (ex.: `45717`)

### Formatos de Hora

- `HH:MM` — recomendado
- `HH:MM:SS`
- Objeto `time` nativo (Excel/openpyxl)

## Normalização de Turnos

### Turnos Padrão (identificados automaticamente)

| Início | Fim | Tipo |
|--------|-----|------|
| 08:00 | 20:00 | Diurno padrão (12h) |
| 20:00 | 08:00 | Noturno padrão (12h, vira dia) |
| 10:00 | 22:00 | Alternativo (12h) |

### Exceções Reais Aceitas

O sistema **não bloqueia** exceções de horário. Turnos fora dos padrões acima são marcados como `is_standard_shift=false` mas são aceitos normalmente:

- `11:00–22:00` (11h)
- `10:00–17:30` (7h30)
- `13:30–22:00` (8h30)
- Qualquer outro intervalo válido (duração entre 30 min e 24h)

### Virada de Dia

Quando `hora_fim <= hora_inicio`, o sistema adiciona automaticamente 1 dia ao horário final:
- `20:00 → 08:00` vira `2026-03-01 20:00 → 2026-03-02 08:00`

## Validações e Diagnóstico

### Erros Fatais (linha marcada como `INVALID`)
- Data ausente ou não parseável
- Hora inicial ausente ou inválida
- Hora final ausente ou inválida
- Duração calculada < 30 min
- Duração calculada > 24h

### Alertas Não-Fatais (linha marcada como `WARNING`)
- Profissional não encontrado no sistema
- Profissional resolvido por correspondência parcial
- Duração declarada diverge da calculada em > 10 min
- Duplicata detectada (mesmo agente + mesmo horário no mesmo lote)
- Sobreposição detectada com outra linha do mesmo agente no mesmo lote

Linhas com `WARNING` **são importadas** na confirmação, desde que o profissional esteja resolvido.  
Linhas com `INVALID` são **sempre ignoradas** na confirmação.

## Matching de Profissional

O sistema tenta resolver o nome do profissional do arquivo para um `User` ativo no banco:

1. Correspondência exata de `User.name` (case-insensitive)
2. Correspondência exata de `User.email`
3. Correspondência parcial (nome do arquivo contido no nome do usuário ou vice-versa)
4. Se múltiplas correspondências → ambíguo (WARNING, não confirmável)
5. Se nenhuma → profissional não encontrado (WARNING, não confirmável)

**Dica**: Use os nomes exatos cadastrados no sistema para evitar alertas de matching.

## Resumo de Contadores

```json
{
  "import_id": 1,
  "total_rows": 10,
  "valid_rows": 8,
  "warning_rows": 1,
  "invalid_rows": 1,
  "duplicate_rows": 0,
  "importable_rows": 9,
  "confirmed": false
}
```

`importable_rows = valid_rows + warning_rows - duplicate_rows`

## Limitações Desta Fase

- **Sem OCR**: apenas arquivos tabulares estruturados (CSV/XLSX)
- **Sem parser de PDF**: PDFs precisam ser convertidos previamente
- **Sem parser de texto livre**: o arquivo deve ter colunas bem definidas
- **Sem LLM/IA**: matching de profissional é por correspondência de string
- **Sem frontend**: toda interação é via API
- **Sem limpeza automática de staging**: `ScheduleImportRow` e `ScheduleImport` ficam no banco indefinidamente (nenhuma purge automática nesta fase)
- **Sem dry-run de sobreposição com DB**: a verificação de sobreposição com turnos existentes só ocorre na confirmação, não no upload

## Rollback

Para reverter a importação de uma determinada escala **antes** da confirmação:
- A confirmação não aconteceu? As linhas de staging não criaram nenhum Shift — basta não confirmar.

Para reverter **depois** da confirmação:
- Exclua os Shifts criados via `DELETE /shifts/{id}` (admin)
- Os `ScheduleImportRow.created_shift_id` apontam para os Shifts criados

Para reverter a migração do banco (tabelas de staging):
```bash
cd /app/backend && alembic downgrade 69a59d22a6f4
```

## Exemplo de Uso via curl

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"sua_senha"}' \
  | jq -r .access_token)

# Upload
curl -X POST http://localhost:8000/schedule-imports/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@escala_marco_2026.csv;type=text/csv" \
  -F "reference_period=2026-03"

# Resumo
curl http://localhost:8000/schedule-imports/1/summary \
  -H "Authorization: Bearer $TOKEN"

# Ver inconsistências
curl "http://localhost:8000/schedule-imports/1/rows?row_status=warning" \
  -H "Authorization: Bearer $TOKEN"

# Confirmar
curl -X POST http://localhost:8000/schedule-imports/1/confirm \
  -H "Authorization: Bearer $TOKEN"

# Baixar relatório
curl http://localhost:8000/schedule-imports/1/report \
  -H "Authorization: Bearer $TOKEN" \
  -o relatorio_inconsistencias.csv
```

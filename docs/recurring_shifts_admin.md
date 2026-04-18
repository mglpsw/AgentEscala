# Recorrência semanal de plantões (Admin)

## Endpoints

- `POST /admin/recurring-shifts/preview`
- `POST /admin/recurring-shifts/confirm`
- `GET /admin/recurring-shifts`
- `GET /admin/recurring-shifts/{id}`

## Regras principais

- recorrência semanal por `weekday` (0=segunda .. 6=domingo)
- preview obrigatório: não cria turnos
- confirmação cria em lote
- limite máximo de geração: 6 meses à frente
- `end_time < start_time` gera plantão cruzando o dia seguinte
- duplicata: mesmo profissional + mesmo intervalo exato
- conflito: sobreposição de horários
- conflitos e duplicatas não são ocultados no preview

## Confirmação granular por item

`POST /admin/recurring-shifts/confirm` aceita `item_decisions` opcional:

```json
{
  "batch_id": 10,
  "item_decisions": [
    { "batch_item_id": 101, "decision": "create", "notes": "ok criar" },
    { "batch_item_id": 102, "decision": "skip", "notes": "pular por conflito" },
    { "batch_item_id": 103, "decision": "keep_existing", "notes": "manter atual" }
  ]
}
```

Decisões suportadas com segurança nesta fase: `create`, `skip`, `keep_existing`.
`overwrite` fica reservado, mas retorna erro por não estar habilitado no fluxo atual.

## Auditoria

A operação salva lote e itens em:

- `recurring_shift_batches`
- `recurring_shift_batch_items`

Com parâmetros, intervalo, status do lote, conflitos/duplicatas e resultado final.

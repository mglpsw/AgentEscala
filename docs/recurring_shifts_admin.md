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

## Auditoria

A operação salva lote e itens em:

- `recurring_shift_batches`
- `recurring_shift_batch_items`

Com parâmetros, intervalo, status do lote, conflitos/duplicatas e resultado final.

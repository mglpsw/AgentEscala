// Tabela de linhas do staging de importação com indicadores visuais por status

// Formata datetime ISO para exibição curta em pt-BR
function formatDateTime(dt) {
  if (!dt) return '—'
  try {
    return new Date(dt).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return String(dt)
  }
}

const STATUS_STYLES = {
  valid:   { row: 'bg-green-50',  badge: 'bg-green-100 text-green-800',   label: 'válida' },
  warning: { row: 'bg-yellow-50', badge: 'bg-yellow-100 text-yellow-800', label: 'alerta' },
  invalid: { row: 'bg-red-50',    badge: 'bg-red-100 text-red-800',       label: 'erro'   },
}

function StatusBadge({ status }) {
  const s = STATUS_STYLES[status] ?? { row: 'bg-gray-50', badge: 'bg-gray-100 text-gray-600', label: status }
  return (
    <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${s.badge}`}>
      {s.label}
    </span>
  )
}

// Resolve o horário a exibir: preferência pelo dado normalizado, fallback para o bruto
function resolveTime(normalized, rawDate, rawTime) {
  const fmt = formatDateTime(normalized)
  if (fmt !== '—') return fmt
  return [rawDate, rawTime].filter(Boolean).join(' ') || '—'
}

// Tabela do staging — cada linha representa uma entrada do arquivo importado
function ImportRowsTable({ rows }) {
  if (!rows || rows.length === 0) {
    return (
      <p className="text-sm text-gray-400 py-6 text-center">
        Nenhuma linha para exibir.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="bg-gray-100 text-gray-600 text-left text-xs uppercase tracking-wide">
            <th className="px-3 py-2 font-medium">#</th>
            <th className="px-3 py-2 font-medium">Profissional</th>
            <th className="px-3 py-2 font-medium">Início</th>
            <th className="px-3 py-2 font-medium">Fim</th>
            <th className="px-3 py-2 font-medium">Status</th>
            <th className="px-3 py-2 font-medium">Confiança</th>
            <th className="px-3 py-2 font-medium">Issues / Observações</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const style = STATUS_STYLES[row.row_status] ?? { row: 'bg-gray-50' }
            return (
              <tr key={row.id} className={`border-t border-gray-100 ${style.row}`}>

                {/* Número da linha no arquivo original */}
                <td className="px-3 py-2 text-gray-400 tabular-nums text-xs">
                  {row.row_number}
                </td>

                {/* Nome do profissional e indicador de identificação */}
                <td className="px-3 py-2">
                  <span className="font-medium text-gray-800">
                    {row.raw_professional || '—'}
                  </span>
                  {row.agent_id ? (
                    <span className="ml-1.5 text-xs text-green-600">(identificado)</span>
                  ) : (
                    <span className="ml-1.5 text-xs text-orange-500">(não identificado)</span>
                  )}
                </td>

                {/* Horário de início — normalizado ou bruto */}
                <td className="px-3 py-2 whitespace-nowrap text-gray-700">
                  {resolveTime(row.normalized_start, row.raw_date, row.raw_start_time)}
                </td>

                {/* Horário de fim — normalizado ou bruto */}
                <td className="px-3 py-2 whitespace-nowrap text-gray-700">
                  {resolveTime(row.normalized_end, null, row.raw_end_time)}
                </td>

                {/* Badges de status, duplicata, sobreposição e turno noturno */}
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-1">
                    <StatusBadge status={row.row_status} />
                    {row.match_status?.includes('ambiguous') && (
                      <span className="px-2 py-0.5 text-xs rounded-full bg-rose-100 text-rose-700 font-medium">
                        ambíguo
                      </span>
                    )}
                    {row.is_duplicate && (
                      <span className="px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-700 font-medium">
                        duplicata
                      </span>
                    )}
                    {row.has_overlap && (
                      <span className="px-2 py-0.5 text-xs rounded-full bg-orange-100 text-orange-700 font-medium">
                        sobreposição
                      </span>
                    )}
                    {row.validation_status === 'conflict' && (
                      <span className="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700 font-medium">
                        conflito
                      </span>
                    )}
                    {row.is_overnight && (
                      <span className="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700 font-medium">
                        noturno
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-3 py-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-gray-700">
                      {typeof row.confidence_score === 'number' ? `${Math.round(row.confidence_score * 100)}%` : '—'}
                    </span>
                    <span className="text-gray-400">
                      {row.parse_status}/{row.match_status}/{row.validation_status}
                    </span>
                  </div>
                </td>

                {/* Issues do backend ou observações brutas do arquivo */}
                <td className="px-3 py-2 text-xs max-w-xs">
                  {row.issues && row.issues.length > 0 ? (
                    <ul className="list-disc list-inside space-y-0.5">
                      {row.issues.map((issue, idx) => (
                        <li key={idx} className="text-amber-700">{issue}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-gray-400">{row.raw_observations || '—'}</span>
                  )}
                </td>

              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default ImportRowsTable

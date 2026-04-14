// Card simples para exibir uma solicitação de troca
// Segue o contrato real do backend
import React from 'react'

const statusColors = {
  pending: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  cancelled: 'bg-gray-100 text-gray-500',
}

function SwapCard({ swap, onCancel, isCancellable }) {
  const statusClass = statusColors[swap.status] || 'bg-gray-100 text-gray-800'
  return (
    <div className="border rounded-lg p-4 mb-3 shadow-sm bg-white flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className={`px-2 py-1 rounded text-xs font-semibold ${statusClass}`}>{swap.status}</span>
        {isCancellable && (
          <button
            className="ml-2 px-3 py-1 text-xs rounded bg-gray-200 hover:bg-gray-300 text-gray-700"
            onClick={() => onCancel(swap.id)}
          >
            Cancelar
          </button>
        )}
      </div>
      <div className="text-sm">
        <div><b>Turno de origem:</b> {swap.origin_shift?.title} ({formatDate(swap.origin_shift?.start_time)})</div>
        <div><b>Turno alvo:</b> {swap.target_shift?.title} ({formatDate(swap.target_shift?.start_time)})</div>
        <div><b>Agente alvo:</b> {swap.target_agent?.name}</div>
        {swap.reason && <div><b>Motivo:</b> {swap.reason}</div>}
        {swap.admin_notes && <div className="text-xs text-gray-500"><b>Obs. admin:</b> {swap.admin_notes}</div>}
      </div>
      <div className="text-xs text-gray-400">Solicitado em {formatDate(swap.created_at, true)}</div>
    </div>
  )
}

function formatDate(dateStr, withTime = false) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return withTime
    ? d.toLocaleString('pt-BR')
    : d.toLocaleDateString('pt-BR')
}

export default SwapCard

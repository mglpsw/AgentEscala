// Card para exibir e aprovar/rejeitar trocas pendentes (admin)
import React, { useState } from 'react'

const statusColors = {
  pending: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  cancelled: 'bg-gray-100 text-gray-500',
}

function PendingSwapCard({ swap, onApprove, onReject, loading }) {
  const [showObs, setShowObs] = useState(false)
  const [obs, setObs] = useState('')
  const [action, setAction] = useState('') // 'approve' | 'reject'

  const handleAction = (type) => {
    setAction(type)
    setShowObs(true)
  }

  const handleConfirm = () => {
    if (action === 'approve') onApprove(swap.id, obs)
    if (action === 'reject') onReject(swap.id, obs)
    setShowObs(false)
    setObs('')
    setAction('')
  }

  return (
    <div className="border rounded-lg p-4 mb-3 shadow-sm bg-white flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className={`px-2 py-1 rounded text-xs font-semibold ${statusColors[swap.status] || 'bg-gray-100 text-gray-800'}`}>{swap.status}</span>
        <div className="flex gap-2">
          <button
            className="px-3 py-1 text-xs rounded bg-green-100 hover:bg-green-200 text-green-800 disabled:opacity-60"
            onClick={() => handleAction('approve')}
            disabled={loading}
          >Aprovar</button>
          <button
            className="px-3 py-1 text-xs rounded bg-red-100 hover:bg-red-200 text-red-800 disabled:opacity-60"
            onClick={() => handleAction('reject')}
            disabled={loading}
          >Rejeitar</button>
        </div>
      </div>
      <div className="text-sm">
        <div><b>Solicitante:</b> {swap.requester?.name}</div>
        <div><b>Turno de origem:</b> {swap.origin_shift?.title} ({formatDate(swap.origin_shift?.start_time)})</div>
        <div><b>Turno alvo:</b> {swap.target_shift?.title} ({formatDate(swap.target_shift?.start_time)})</div>
        <div><b>Agente alvo:</b> {swap.target_agent?.name}</div>
        {swap.reason && <div><b>Motivo:</b> {swap.reason}</div>}
        {swap.admin_notes && <div className="text-xs text-gray-500"><b>Obs. admin:</b> {swap.admin_notes}</div>}
      </div>
      <div className="text-xs text-gray-400">Solicitado em {formatDate(swap.created_at, true)}</div>
      {showObs && (
        <div className="mt-2 flex flex-col gap-2">
          <label className="text-xs font-medium">Observação (opcional)</label>
          <textarea
            className="border rounded px-2 py-1 text-sm"
            value={obs}
            onChange={e => setObs(e.target.value)}
            maxLength={200}
            rows={2}
            autoFocus
          />
          <div className="flex gap-2">
            <button
              className="px-3 py-1 text-xs rounded bg-blue-600 text-white hover:bg-blue-700"
              onClick={handleConfirm}
              disabled={loading}
            >Confirmar</button>
            <button
              className="px-3 py-1 text-xs rounded bg-gray-200 hover:bg-gray-300"
              onClick={() => { setShowObs(false); setObs(''); setAction('') }}
              disabled={loading}
            >Cancelar</button>
          </div>
        </div>
      )}
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

export default PendingSwapCard

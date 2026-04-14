// Formulário para criar nova solicitação de troca
// Busca shifts do usuário e shifts de outros agentes
import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import useAuth from '../hooks/use_auth.js'

function SwapForm({ onCreated }) {
  const { user } = useAuth()
  const [myShifts, setMyShifts] = useState([])
  const [otherShifts, setOtherShifts] = useState([])
  const [targetAgentId, setTargetAgentId] = useState('')
  const [originShiftId, setOriginShiftId] = useState('')
  const [targetShiftId, setTargetShiftId] = useState('')
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Carrega turnos do usuário logado
  useEffect(() => {
    if (!user) return
    api.get(`/shifts/agent/${user.id}`)
      .then(res => setMyShifts(res.data))
      .catch(() => setMyShifts([]))
  }, [user])

  // Carrega turnos de outros agentes
  useEffect(() => {
    api.get('/shifts')
      .then(res => {
        // Filtra apenas turnos de outros agentes
        setOtherShifts(res.data.filter(s => s.agent_id !== user?.id))
      })
      .catch(() => setOtherShifts([]))
  }, [user])

  // Atualiza targetAgentId ao escolher target_shift
  useEffect(() => {
    if (!targetShiftId) return setTargetAgentId('')
    const shift = otherShifts.find(s => String(s.id) === String(targetShiftId))
    setTargetAgentId(shift ? shift.agent_id : '')
  }, [targetShiftId, otherShifts])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')
    try {
      await api.post('/swaps', {
        target_agent_id: Number(targetAgentId),
        origin_shift_id: Number(originShiftId),
        target_shift_id: Number(targetShiftId),
        reason: reason || undefined,
      })
      setSuccess('Solicitação enviada com sucesso!')
      setOriginShiftId('')
      setTargetShiftId('')
      setReason('')
      if (onCreated) onCreated()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Erro ao criar solicitação')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className="bg-white border rounded-lg p-4 mb-6 shadow-sm flex flex-col gap-3" onSubmit={handleSubmit}>
      <div className="font-semibold text-lg mb-1">Nova solicitação de troca</div>
      <div className="flex flex-col md:flex-row gap-3">
        <div className="flex-1">
          <label className="block text-sm font-medium mb-1">Seu turno</label>
          <select
            className="w-full border rounded px-2 py-1"
            value={originShiftId}
            onChange={e => setOriginShiftId(e.target.value)}
            required
          >
            <option value="">Selecione</option>
            {myShifts.map(s => (
              <option key={s.id} value={s.id}>
                {formatShift(s)}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-sm font-medium mb-1">Turno alvo</label>
          <select
            className="w-full border rounded px-2 py-1"
            value={targetShiftId}
            onChange={e => setTargetShiftId(e.target.value)}
            required
          >
            <option value="">Selecione</option>
            {otherShifts.map(s => (
              <option key={s.id} value={s.id}>
                {formatShift(s)} — {s.agent?.name || s.agent_id}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Motivo (opcional)</label>
        <input
          className="w-full border rounded px-2 py-1"
          value={reason}
          onChange={e => setReason(e.target.value)}
          maxLength={200}
        />
      </div>
      <div className="flex gap-2 items-center">
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-60"
          disabled={loading || !originShiftId || !targetShiftId}
        >
          {loading ? 'Enviando...' : 'Solicitar troca'}
        </button>
        {success && <span className="text-green-600 text-sm">{success}</span>}
        {error && <span className="text-red-600 text-sm">{error}</span>}
      </div>
    </form>
  )
}

function formatShift(s) {
  if (!s) return '-'
  const ini = new Date(s.start_time)
  const end = new Date(s.end_time)
  return `${ini.toLocaleDateString('pt-BR')} ${ini.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})} - ${end.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})}`
}

export default SwapForm

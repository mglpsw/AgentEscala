import { useEffect, useMemo, useState } from 'react'
import api from '../api/client.js'

const PLANTAO_OPTIONS = [
  { label: '12H DIA (08-20)', key: '12H DIA', start: '08:00', end: '20:00' },
  { label: '10-22H', key: '10-22H', start: '10:00', end: '22:00' },
  { label: '12H NOITE (20-08)', key: '12H NOITE', start: '20:00', end: '08:00' },
  { label: '24 HORAS', key: '24 HORAS', start: '00:00', end: '00:00' },
]

function buildDateTime(date, hhmm) {
  return `${date}T${hhmm}:00`
}

function nextDay(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`)
  d.setDate(d.getDate() + 1)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export default function AdminPlantoesPage() {
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [users, setUsers] = useState([])
  const [shifts, setShifts] = useState([])
  const [coverage, setCoverage] = useState(null)
  const [selectedUserId, setSelectedUserId] = useState('')
  const [selectedPlantao, setSelectedPlantao] = useState(PLANTAO_OPTIONS[0].key)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const loadData = async () => {
    setError('')
    try {
      const [usersResp, shiftsResp, coverageResp] = await Promise.all([
        api.get('/users/agents'),
        api.get('/shifts', { params: { limit: 500 } }),
        api.get('/shifts/coverage/flags', { params: { start_date: date, end_date: date } }),
      ])
      setUsers(usersResp.data)
      const dayShifts = shiftsResp.data.filter((s) => s.start_time?.slice(0, 10) === date)
      setShifts(dayShifts)
      setCoverage(coverageResp.data?.[0] ?? null)
      if (!selectedUserId && usersResp.data.length > 0) {
        setSelectedUserId(String(usersResp.data[0].id))
      }
    } catch {
      setError('Não foi possível carregar dados de plantão.')
    }
  }

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date])

  const byType = useMemo(() => {
    const map = { '12H DIA': 0, '10-22H': 0, '12H NOITE': 0 }
    shifts.forEach((s) => {
      const title = (s.title || '').toUpperCase()
      if (map[title] !== undefined) map[title] += 1
    })
    return map
  }, [shifts])

  const handleAdd = async () => {
    if (!selectedUserId) return
    setLoading(true)
    setError('')
    try {
      const selected = PLANTAO_OPTIONS.find((p) => p.key === selectedPlantao)
      const startDate = date
      const endDate = selected.end === '08:00' && selected.start === '20:00' ? nextDay(date) : date
      const payload = {
        agent_id: Number(selectedUserId),
        user_id: Number(selectedUserId),
        title: selected.key,
        start_time: buildDateTime(startDate, selected.start),
        end_time: buildDateTime(endDate, selected.end),
      }
      await api.post('/shifts/', payload)
      await loadData()
    } catch (e) {
      setError(e?.response?.data?.detail || 'Falha ao adicionar plantão.')
    } finally {
      setLoading(false)
    }
  }

  const handleRemove = async (shiftId) => {
    setLoading(true)
    setError('')
    try {
      await api.delete(`/shifts/${shiftId}`)
      await loadData()
    } catch {
      setError('Falha ao remover plantão.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-bold text-gray-800">Painel Admin de Plantões</h2>
        <p className="text-sm text-gray-600">Adicionar/remover médicos por classe de plantão e validar cobertura diária.</p>
      </header>

      <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-4">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs text-gray-600 mb-1">Data</label>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="rounded border px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Médico</label>
            <select value={selectedUserId} onChange={(e) => setSelectedUserId(e.target.value)} className="rounded border px-3 py-2 text-sm min-w-52">
              {users.map((u) => (
                <option key={u.id} value={u.id}>{u.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Classe</label>
            <select value={selectedPlantao} onChange={(e) => setSelectedPlantao(e.target.value)} className="rounded border px-3 py-2 text-sm min-w-48">
              {PLANTAO_OPTIONS.map((p) => (
                <option key={p.key} value={p.key}>{p.label}</option>
              ))}
            </select>
          </div>
          <button onClick={handleAdd} disabled={loading} className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50">
            Adicionar plantão
          </button>
        </div>

        {coverage ? (
          <div className={`rounded border px-3 py-2 text-sm ${coverage.complete ? 'border-green-200 bg-green-50 text-green-700' : 'border-red-200 bg-red-50 text-red-700'}`}>
            {coverage.complete
              ? 'Dia completo ✅'
              : `Dia incompleto ⚠️ Faltam: 12H DIA=${coverage.missing['12H DIA']}, 10-22H=${coverage.missing['10-22H']}, 12H NOITE=${coverage.missing['12H NOITE']}`}
          </div>
        ) : null}

        <div className="text-xs text-gray-600">Contagem atual: 12H DIA={byType['12H DIA']} · 10-22H={byType['10-22H']} · 12H NOITE={byType['12H NOITE']}</div>

        {error ? <p className="text-sm text-red-600">{error}</p> : null}
      </section>

      <section className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b text-sm font-semibold text-gray-700">Plantões do dia ({shifts.length})</div>
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-600">
            <tr>
              <th className="px-4 py-2 text-left">Médico</th>
              <th className="px-4 py-2 text-left">Classe</th>
              <th className="px-4 py-2 text-left">Início</th>
              <th className="px-4 py-2 text-left">Fim</th>
              <th className="px-4 py-2 text-left">Ação</th>
            </tr>
          </thead>
          <tbody>
            {shifts.map((shift) => (
              <tr key={shift.id} className="border-t">
                <td className="px-4 py-2">{shift.agent?.name || '-'}</td>
                <td className="px-4 py-2">{shift.title}</td>
                <td className="px-4 py-2">{new Date(shift.start_time).toLocaleString('pt-BR')}</td>
                <td className="px-4 py-2">{new Date(shift.end_time).toLocaleString('pt-BR')}</td>
                <td className="px-4 py-2">
                  <button onClick={() => handleRemove(shift.id)} className="text-red-600 hover:text-red-700" disabled={loading}>
                    remover
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}

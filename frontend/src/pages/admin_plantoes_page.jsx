import { useEffect, useMemo, useState } from 'react'
import api from '../api/client.js'

const PLANTAO_OPTIONS = [
  { label: '12H DIA (08-20)', key: '12H DIA', start: '08:00', end: '20:00' },
  { label: '10-22H', key: '10-22H', start: '10:00', end: '22:00' },
  { label: '12H NOITE (20-08)', key: '12H NOITE', start: '20:00', end: '08:00' },
  { label: '24 HORAS', key: '24 HORAS', start: '00:00', end: '00:00' },
]

const SHIFT_TYPES = {
  DAY: '12H DIA',
  NIGHT: '12H NOITE',
  INTER: '10-22H',
  FULL: '24 HORAS',
}

const EXTRA_OPTIONS = [
  { key: SHIFT_TYPES.DAY, label: '12H DIA (08-20)', start: '08:00', end: '20:00' },
  { key: SHIFT_TYPES.INTER, label: '10-22H', start: '10:00', end: '22:00' },
  { key: SHIFT_TYPES.NIGHT, label: '12H NOITE (20-08)', start: '20:00', end: '08:00' },
  { key: SHIFT_TYPES.FULL, label: '24 HORAS', start: '00:00', end: '00:00' },
]
const WEEKDAY_OPTIONS = [
  { value: 0, label: 'Segunda-feira' },
  { value: 1, label: 'Terça-feira' },
  { value: 2, label: 'Quarta-feira' },
  { value: 3, label: 'Quinta-feira' },
  { value: 4, label: 'Sexta-feira' },
  { value: 5, label: 'Sábado' },
  { value: 6, label: 'Domingo' },
]

function nextDay(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`)
  d.setDate(d.getDate() + 1)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function buildDateTime(date, hhmm) {
  return `${date}T${hhmm}:00`
}

function slotTemplate(firstType) {
  if (firstType === SHIFT_TYPES.FULL) {
    return [
      { id: 'slot_24h_1', label: 'Plantonista 24h #1', type: SHIFT_TYPES.FULL, editableType: false },
      { id: 'slot_24h_2', label: 'Plantonista 24h #2', type: SHIFT_TYPES.FULL, editableType: false },
    ]
  }

  return [
    { id: 'slot_day_1', label: 'Plantonista Dia #1', type: firstType || SHIFT_TYPES.DAY, editableType: true },
    { id: 'slot_day_2', label: 'Plantonista Dia #2', type: SHIFT_TYPES.DAY, editableType: false },
    { id: 'slot_inter', label: 'Intermediário', type: SHIFT_TYPES.INTER, editableType: false },
    { id: 'slot_night', label: 'Noturno', type: SHIFT_TYPES.NIGHT, editableType: false },
  ]
}

function createShiftPayload({ date, userId, shiftType }) {
  if (shiftType === SHIFT_TYPES.DAY) {
    return { agent_id: userId, user_id: userId, title: shiftType, start_time: buildDateTime(date, '08:00'), end_time: buildDateTime(date, '20:00') }
  }
  if (shiftType === SHIFT_TYPES.INTER) {
    return { agent_id: userId, user_id: userId, title: shiftType, start_time: buildDateTime(date, '10:00'), end_time: buildDateTime(date, '22:00') }
  }
  if (shiftType === SHIFT_TYPES.NIGHT) {
    return { agent_id: userId, user_id: userId, title: shiftType, start_time: buildDateTime(date, '20:00'), end_time: buildDateTime(nextDay(date), '08:00') }
  }
  return { agent_id: userId, user_id: userId, title: SHIFT_TYPES.FULL, start_time: buildDateTime(date, '00:00'), end_time: buildDateTime(nextDay(date), '00:00') }
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
  const [extraUserId, setExtraUserId] = useState('')
  const [extraType, setExtraType] = useState(SHIFT_TYPES.DAY)

  const [firstType, setFirstType] = useState(SHIFT_TYPES.DAY)
  const [slotAssignments, setSlotAssignments] = useState({})
  const [recurringForm, setRecurringForm] = useState({
    user_id: '',
    weekday: 0,
    shift_label: SHIFT_TYPES.DAY,
    start_time: '08:00',
    end_time: '20:00',
    start_date: new Date().toISOString().slice(0, 10),
    months_ahead: 1,
    notes: '',
  })
  const [recurringPreview, setRecurringPreview] = useState(null)
  const [itemDecisions, setItemDecisions] = useState({})

  const template = useMemo(() => slotTemplate(firstType), [firstType])

  const loadData = async () => {
    setError('')
    try {
      const [usersResp, shiftsResp, coverageResp] = await Promise.all([
        api.get('/users/agents'),
        api.get('/shifts/', { params: { limit: 500 } }),
        api.get('/shifts/coverage/flags', { params: { start_date: date, end_date: date } }),
      ])
      setUsers(usersResp.data)
      const dayShifts = shiftsResp.data.filter((s) => s.start_time?.slice(0, 10) === date)
      setShifts(dayShifts)
      setCoverage(coverageResp.data?.[0] ?? null)
      if (!selectedUserId && usersResp.data.length > 0) {
        setSelectedUserId(String(usersResp.data[0].id))
      }
      if (!extraUserId && usersResp.data.length > 0) setExtraUserId(String(usersResp.data[0].id))
      if (!recurringForm.user_id && usersResp.data.length > 0) {
        setRecurringForm((prev) => ({ ...prev, user_id: String(usersResp.data[0].id) }))
      }
      setShifts(shiftsResp.data.filter((s) => s.start_time?.slice(0, 10) === date))
      setCoverage(coverageResp.data?.[0] ?? null)
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

  const handleSlotChange = (slotId, userId) => {
    setSlotAssignments((prev) => ({ ...prev, [slotId]: userId }))
  }

  const handleApplyTemplate = async () => {
    setLoading(true)
    setError('')
    try {
      for (const slot of template) {
        const userId = Number(slotAssignments[slot.id] || 0)
        if (!userId) continue
        await api.post('/shifts/', createShiftPayload({ date, userId, shiftType: slot.type }))
      }
      await loadData()
    } catch (e) {
      setError(e?.response?.data?.detail || 'Falha ao aplicar escala padrão do dia.')
    } finally {
      setLoading(false)
    }
  }

  const handleAddExtra = async () => {
    setLoading(true)
    setError('')
    try {
      const payload = createShiftPayload({ date, userId: Number(extraUserId), shiftType: extraType })
      await api.post('/shifts/', payload)
      await loadData()
    } catch (e) {
      setError(e?.response?.data?.detail || 'Falha ao adicionar turno extra.')
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

  const handleRecurringPreview = async () => {
    setLoading(true)
    setError('')
    try {
      const payload = {
        ...recurringForm,
        user_id: Number(recurringForm.user_id),
        weekday: Number(recurringForm.weekday),
        months_ahead: Number(recurringForm.months_ahead),
      }
      const { data } = await api.post('/admin/recurring-shifts/preview', payload)
      setRecurringPreview(data)
      const defaults = {}
      ;(data.items || []).forEach((item) => {
        defaults[item.batch_item_id] = {
          decision: item.conflict_status || item.duplicate_status ? 'skip' : 'create',
          notes: '',
        }
      })
      setItemDecisions(defaults)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Falha ao gerar preview da recorrência.')
    } finally {
      setLoading(false)
    }
  }

  const handleRecurringConfirm = async () => {
    if (!recurringPreview) return
    setLoading(true)
    setError('')
    try {
      const payload = {
        ...recurringForm,
        user_id: Number(recurringForm.user_id),
        weekday: Number(recurringForm.weekday),
        months_ahead: Number(recurringForm.months_ahead),
        batch_id: recurringPreview.batch_id,
        include_conflicts: false,
        include_duplicates: false,
        item_decisions: Object.entries(itemDecisions).map(([batchItemId, val]) => ({
          batch_item_id: Number(batchItemId),
          decision: val.decision,
          notes: val.notes || null,
        })),
      }
      const { data } = await api.post('/admin/recurring-shifts/confirm', payload)
      await loadData()
      setRecurringPreview((prev) => ({ ...prev, result: data }))
    } catch (e) {
      setError(e?.response?.data?.detail || 'Falha ao confirmar recorrência semanal.')
    } finally {
      setLoading(false)
    }
  }

  const totals = useMemo(() => {
    if (!recurringPreview?.items) return { create: 0, skip: 0, keep: 0, total: 0, normal: 0, conflict: 0, duplicate: 0 }
    const t = { create: 0, skip: 0, keep: 0, total: recurringPreview.items.length, normal: 0, conflict: 0, duplicate: 0 }
    recurringPreview.items.forEach((item) => {
      if (!item.conflict_status && !item.duplicate_status) t.normal += 1
      if (item.conflict_status) t.conflict += 1
      if (item.duplicate_status) t.duplicate += 1
      const d = itemDecisions[item.batch_item_id]?.decision
      if (d === 'create') t.create += 1
      if (d === 'skip') t.skip += 1
      if (d === 'keep_existing') t.keep += 1
    })
    return t
  }, [recurringPreview, itemDecisions])

  const countsByType = useMemo(() => {
    const map = { [SHIFT_TYPES.DAY]: 0, [SHIFT_TYPES.INTER]: 0, [SHIFT_TYPES.NIGHT]: 0, [SHIFT_TYPES.FULL]: 0 }
    shifts.forEach((s) => {
      const key = (s.title || '').toUpperCase().trim()
      if (map[key] !== undefined) map[key] += 1
    })
    return map
  }, [shifts])

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-bold text-gray-800">Painel Admin de Plantões</h2>
        <p className="text-sm text-gray-600">Adicionar/remover médicos por classe de plantão e validar cobertura diária.</p>
        <p className="text-sm text-gray-600">Padrão diário com 4 campos (ou 2 campos 24h) + opção de turno extra individual.</p>
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
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-4">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs text-gray-600 mb-1">1º campo (selecionável)</label>
            <select value={firstType} onChange={(e) => setFirstType(e.target.value)} className="rounded border px-3 py-2 text-sm">
              <option value={SHIFT_TYPES.DAY}>12H DIA</option>
              <option value={SHIFT_TYPES.FULL}>24 HORAS</option>
            </select>
          </div>
          <button onClick={handleApplyTemplate} disabled={loading} className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50">
            Aplicar padrão do dia
          </button>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          {template.map((slot) => (
            <div key={slot.id} className="rounded border p-3">
              <p className="text-xs text-gray-500">{slot.label}</p>
              <p className="text-sm font-semibold text-gray-700 mb-2">{slot.type}</p>
              <select
                value={slotAssignments[slot.id] || ''}
                onChange={(e) => handleSlotChange(slot.id, e.target.value)}
                className="rounded border px-3 py-2 text-sm w-full"
              >
                <option value="">Selecione médico...</option>
                {users.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
              </select>
            </div>
          ))}
        </div>

        {coverage ? (
          <div className={`rounded border px-3 py-2 text-sm ${coverage.complete ? 'border-green-200 bg-green-50 text-green-700' : 'border-red-200 bg-red-50 text-red-700'}`}>
            {coverage.complete ? 'Dia completo ✅' : `Dia incompleto ⚠️ Faltam: 12H DIA=${coverage.missing['12H DIA']}, 10-22H=${coverage.missing['10-22H']}, 12H NOITE=${coverage.missing['12H NOITE']}`}
          </div>
        ) : null}

        <div className="text-xs text-gray-600">
          Contagem atual: DIA={countsByType[SHIFT_TYPES.DAY]} · INTER={countsByType[SHIFT_TYPES.INTER]} · NOITE={countsByType[SHIFT_TYPES.NIGHT]} · 24H={countsByType[SHIFT_TYPES.FULL]}
        </div>

        <div className="rounded border border-dashed border-gray-300 p-3 space-y-2">
          <p className="text-sm font-semibold text-gray-700">Funções admin — turno extra individual</p>
          <div className="flex gap-3 flex-wrap items-end">
            <div>
              <label className="block text-xs text-gray-600 mb-1">Médico</label>
              <select value={extraUserId} onChange={(e) => setExtraUserId(e.target.value)} className="rounded border px-3 py-2 text-sm min-w-56">
                {users.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Turno extra</label>
              <select value={extraType} onChange={(e) => setExtraType(e.target.value)} className="rounded border px-3 py-2 text-sm min-w-44">
                {EXTRA_OPTIONS.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
              </select>
            </div>
            <button onClick={handleAddExtra} disabled={loading} className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
              Adicionar extra
            </button>
          </div>
        </div>

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

      <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-4">
        <h3 className="text-lg font-semibold text-gray-800">Criar recorrência semanal</h3>
        <p className="text-xs text-gray-500">Preview obrigatório. Limite máximo de 6 meses.</p>
        <div className="grid gap-3 md:grid-cols-4">
          <div>
            <label className="block text-xs text-gray-600 mb-1">Profissional</label>
            <select
              value={recurringForm.user_id}
              onChange={(e) => setRecurringForm((p) => ({ ...p, user_id: e.target.value }))}
              className="rounded border px-3 py-2 text-sm w-full"
            >
              {users.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Dia da semana</label>
            <select
              value={recurringForm.weekday}
              onChange={(e) => setRecurringForm((p) => ({ ...p, weekday: Number(e.target.value) }))}
              className="rounded border px-3 py-2 text-sm w-full"
            >
              {WEEKDAY_OPTIONS.map((w) => <option key={w.value} value={w.value}>{w.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Turno</label>
            <select
              value={recurringForm.shift_label}
              onChange={(e) => {
                const selected = EXTRA_OPTIONS.find((item) => item.key === e.target.value)
                setRecurringForm((p) => ({ ...p, shift_label: e.target.value, start_time: selected?.start || p.start_time, end_time: selected?.end || p.end_time }))
              }}
              className="rounded border px-3 py-2 text-sm w-full"
            >
              {EXTRA_OPTIONS.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Data inicial</label>
            <input type="date" value={recurringForm.start_date} onChange={(e) => setRecurringForm((p) => ({ ...p, start_date: e.target.value }))} className="rounded border px-3 py-2 text-sm w-full" />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Hora início</label>
            <input type="time" value={recurringForm.start_time} onChange={(e) => setRecurringForm((p) => ({ ...p, start_time: e.target.value }))} className="rounded border px-3 py-2 text-sm w-full" />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Hora fim</label>
            <input type="time" value={recurringForm.end_time} onChange={(e) => setRecurringForm((p) => ({ ...p, end_time: e.target.value }))} className="rounded border px-3 py-2 text-sm w-full" />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Meses</label>
            <input type="number" min="1" max="6" value={recurringForm.months_ahead} onChange={(e) => setRecurringForm((p) => ({ ...p, months_ahead: Math.max(1, Math.min(6, Number(e.target.value) || 1)) }))} className="rounded border px-3 py-2 text-sm w-full" />
          </div>
          <div className="md:col-span-4">
            <label className="block text-xs text-gray-600 mb-1">Notas</label>
            <input type="text" value={recurringForm.notes} onChange={(e) => setRecurringForm((p) => ({ ...p, notes: e.target.value }))} className="rounded border px-3 py-2 text-sm w-full" />
          </div>
        </div>

        <div className="flex gap-2">
          <button onClick={handleRecurringPreview} disabled={loading || !recurringForm.user_id} className="rounded bg-slate-700 px-4 py-2 text-sm text-white disabled:opacity-50">Gerar preview</button>
          <button onClick={handleRecurringConfirm} disabled={loading || !recurringPreview} className="rounded bg-green-600 px-4 py-2 text-sm text-white disabled:opacity-50">Confirmar criação em lote</button>
        </div>

        {recurringPreview ? (
          <div className="rounded border border-gray-200 p-3">
            <p className="text-sm text-gray-700">
              Intervalo: {recurringPreview.interval_start} até {recurringPreview.interval_end} ·
              Total: {recurringPreview.total_generated} ·
              Conflitos: {recurringPreview.total_conflicts} ·
              Duplicatas: {recurringPreview.total_duplicates}
            </p>
            <p className="text-xs text-gray-600 mt-1">
              Normais: {totals.normal} · Selecionados criar: {totals.create} · Selecionados pular: {totals.skip} · Manter existente: {totals.keep}
            </p>
            {recurringPreview?.result ? (
              <p className="text-sm text-green-700 mt-1">
                Criados: {recurringPreview.result.total_created} · Pulados: {recurringPreview.result.skipped}
              </p>
            ) : null}
            <div className="max-h-56 overflow-auto mt-2 border rounded">
              <table className="min-w-full text-xs">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-2 py-1 text-left">Data</th>
                    <th className="px-2 py-1 text-left">Início</th>
                    <th className="px-2 py-1 text-left">Fim</th>
                    <th className="px-2 py-1 text-left">Status</th>
                    <th className="px-2 py-1 text-left">Decisão</th>
                    <th className="px-2 py-1 text-left">Nota</th>
                  </tr>
                </thead>
                <tbody>
                  {recurringPreview.items.map((item) => (
                    <tr key={`${item.target_date}-${item.start_datetime}`} className="border-t">
                      <td className="px-2 py-1">{item.target_date}</td>
                      <td className="px-2 py-1">{new Date(item.start_datetime).toLocaleString('pt-BR')}</td>
                      <td className="px-2 py-1">{new Date(item.end_datetime).toLocaleString('pt-BR')}</td>
                      <td className="px-2 py-1">
                        {item.duplicate_status ? `Duplicata (${item.existing_shift_id || '-'})` : item.conflict_status ? `Conflito (${item.existing_shift_id || '-'})` : 'OK'}
                      </td>
                      <td className="px-2 py-1">
                        <select
                          value={itemDecisions[item.batch_item_id]?.decision || 'create'}
                          onChange={(e) => setItemDecisions((prev) => ({ ...prev, [item.batch_item_id]: { ...(prev[item.batch_item_id] || {}), decision: e.target.value } }))}
                          className="rounded border px-1 py-1"
                        >
                          <option value="create">Criar</option>
                          <option value="skip">Pular</option>
                          <option value="keep_existing">Manter existente</option>
                        </select>
                      </td>
                      <td className="px-2 py-1">
                        <input
                          value={itemDecisions[item.batch_item_id]?.notes || ''}
                          onChange={(e) => setItemDecisions((prev) => ({ ...prev, [item.batch_item_id]: { ...(prev[item.batch_item_id] || {}), notes: e.target.value } }))}
                          className="rounded border px-1 py-1 w-40"
                          placeholder="Nota da decisão"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  )
}

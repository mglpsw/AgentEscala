import { useMemo, useState } from 'react'
import api from '../api/client.js'
import ImportRowsTable from '../components/import_rows_table.jsx'

const STATE = { IDLE: 'idle', UPLOADING: 'uploading', REVIEWING: 'reviewing', CONFIRMING: 'confirming', CONFIRMED: 'confirmed' }

const SHIFT_KIND_STYLES = {
  day: 'bg-green-100 text-green-800 border-green-200',
  intermediate: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  night: 'bg-blue-100 text-blue-800 border-blue-200',
  twenty_four: 'bg-purple-100 text-purple-800 border-purple-200',
  custom: 'bg-gray-100 text-gray-800 border-gray-200',
}

const EDITABLE_OCR_FIELDS = ['professional_name_raw', 'start_time_raw', 'end_time_raw', 'shift_kind']

function buildOcrRowKey(row) {
  const sheet = (row?.source_sheet || '').trim() || 'no-sheet'
  const page = row?.source_page ?? 'no-page'
  const index = row?.source_row_index ?? 'no-row'
  return `${sheet}::${page}::${index}`
}

function extractShiftsCreated(summary) {
  const match = summary?.source_description?.match(/Turnos criados nesta confirmação:\s*(\d+)/)
  return match ? parseInt(match[1], 10) : null
}

function fmtDateTime(dt) {
  if (!dt) return '—'
  try {
    return new Date(dt).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return String(dt)
  }
}

function ErrorMessage({ message }) {
  if (!message) return null
  return <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">{message}</p>
}

function SummaryBadges({ summary }) {
  const items = [
    { label: 'Total', value: summary.total_rows, cls: 'bg-gray-100 text-gray-700' },
    { label: 'Válidas', value: summary.valid_rows, cls: 'bg-green-100 text-green-800' },
    { label: 'Alertas', value: summary.warning_rows, cls: 'bg-yellow-100 text-yellow-800' },
    { label: 'Erros', value: summary.invalid_rows, cls: 'bg-red-100 text-red-800' },
    { label: 'Duplicatas', value: summary.duplicate_rows, cls: 'bg-purple-100 text-purple-800' },
    { label: 'Importáveis', value: summary.importable_rows, cls: 'bg-blue-100 text-blue-800' },
  ]
  return <div className="flex flex-wrap gap-2">{items.map(({ label, value, cls }) => <span key={label} className={`px-3 py-1 rounded-full text-sm font-semibold ${cls}`}>{label}: {value}</span>)}</div>
}

function UploadForm({ selectedFile, referencePeriod, sourceDescription, isUploading, error, onFileChange, onReferencePeriodChange, onSourceDescriptionChange, onSubmit }) {
  return (
    <div className="max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-1">Importar Escala</h1>
        <p className="text-sm text-gray-500">Envie CSV/XLSX/PDF/Imagem. Fluxo mantido: parse → preview → staging → revisão → confirmação.</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 md:p-6">
        <h2 className="text-base font-semibold text-gray-700 mb-4">Selecionar arquivo</h2>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label htmlFor="import-file" className="block text-sm font-medium text-gray-700 mb-1">Arquivo <span className="text-red-500">*</span></label>
            <input id="import-file" type="file" accept=".csv,.xlsx,.xls,.pdf,.png,.jpg,.jpeg,.webp,.tiff" required onChange={onFileChange} className="block w-full text-sm text-gray-700 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer" />
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label htmlFor="reference-period" className="block text-sm font-medium text-gray-700 mb-1">Período referência</label>
              <input id="reference-period" type="text" value={referencePeriod} onChange={onReferencePeriodChange} placeholder="Ex.: 2026-03" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label htmlFor="source-desc" className="block text-sm font-medium text-gray-700 mb-1">Descrição da origem</label>
              <input id="source-desc" type="text" value={sourceDescription} onChange={onSourceDescriptionChange} placeholder="Ex.: Escala março do setor A" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
          <ErrorMessage message={error} />
          <button type="submit" disabled={!selectedFile || isUploading} className="w-full bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">{isUploading ? 'Processando...' : 'Enviar e validar'}</button>
        </form>
      </div>
    </div>
  )
}

function OcrSideSummary({ groupedDays }) {
  const all = Object.values(groupedDays)
  const stats = {
    days: all.length,
    validDays: all.filter((d) => d.overallScore >= 0.95).length,
    conflictDays: all.filter((d) => d.alerts.some((a) => /conflito|ambíguo/i.test(a))).length,
    missingShiftDays: all.filter((d) => d.alerts.some((a) => /falt|duplicado/i.test(a))).length,
    ambiguous: all.reduce((acc, d) => acc + d.rows.filter((r) => r.match_status === 'ambiguous').length, 0),
    newUsers: all.reduce((acc, d) => acc + d.rows.filter((r) => r.match_status === 'new_user_candidate').length, 0),
    crmEnrichments: all.reduce((acc, d) => acc + d.rows.filter((r) => r.suggested_profile_enrichment?.type === 'add_crm').length, 0),
    crmConflicts: all.reduce((acc, d) => acc + d.rows.filter((r) => r.validation_messages?.some((m) => /crm.*conflito/i.test(m))).length, 0),
  }

  return (
    <aside className="rounded-xl border border-gray-200 bg-white p-4 text-xs space-y-2">
      <h4 className="text-sm font-semibold text-gray-700">Resumo OCR por dia</h4>
      <p>Total de dias: <strong>{stats.days}</strong></p>
      <p>Dias válidos: <strong>{stats.validDays}</strong></p>
      <p>Dias com conflito: <strong>{stats.conflictDays}</strong></p>
      <p>Dias com turno faltando/duplicado: <strong>{stats.missingShiftDays}</strong></p>
      <p>Linhas ambíguas: <strong>{stats.ambiguous}</strong></p>
      <p>Novos usuários: <strong>{stats.newUsers}</strong></p>
      <p>Sugestões de CRM: <strong>{stats.crmEnrichments}</strong></p>
      <p>Conflitos de CRM: <strong>{stats.crmConflicts}</strong></p>
    </aside>
  )
}

function OcrDayCards({ groupedDays, onInlineEdit }) {
  const dayKeys = Object.keys(groupedDays).sort()
  if (dayKeys.length === 0) return null
  return (
    <div className="space-y-4">
      {dayKeys.map((key) => {
        const day = groupedDays[key]
        return (
          <article key={key} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap gap-2 items-center justify-between mb-3">
              <div>
                <h3 className="font-semibold text-gray-800">{day.dateLabel} ({day.weekday || '—'})</h3>
                <p className="text-xs text-gray-500">Layout: {day.layoutType} · Score dia: {Math.round(day.overallScore * 100)}%</p>
              </div>
              <div className="flex flex-wrap gap-1">{day.alerts.map((alert) => <span key={alert} className="px-2 py-1 rounded-full text-[11px] bg-rose-50 text-rose-700">{alert}</span>)}</div>
            </div>

            <div className="space-y-2">
              {day.rows.map((row) => (
                <div key={row._ui_row_key || `${key}-${row.source_row_index}`} className={`rounded border p-3 text-xs ${row._ui_isAnomalous ? 'border-rose-200 bg-rose-50/30' : 'border-gray-100'}`}>
                  <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-4">
                    <label className="space-y-1"><span className="text-gray-500">Nome bruto</span><input value={row.professional_name_raw || ''} onChange={(e) => onInlineEdit(row._ui_row_key, 'professional_name_raw', e.target.value)} className="w-full rounded border px-2 py-1" /></label>
                    <label className="space-y-1"><span className="text-gray-500">Horário início</span><input value={row.start_time_raw || ''} onChange={(e) => onInlineEdit(row._ui_row_key, 'start_time_raw', e.target.value)} className="w-full rounded border px-2 py-1" /></label>
                    <label className="space-y-1"><span className="text-gray-500">Horário fim</span><input value={row.end_time_raw || ''} onChange={(e) => onInlineEdit(row._ui_row_key, 'end_time_raw', e.target.value)} className="w-full rounded border px-2 py-1" /></label>
                    <label className="space-y-1"><span className="text-gray-500">Turno</span><select value={row.shift_kind || 'custom'} onChange={(e) => onInlineEdit(row._ui_row_key, 'shift_kind', e.target.value)} className="w-full rounded border px-2 py-1"><option value="day">day</option><option value="intermediate">intermediate</option><option value="night">night</option><option value="twenty_four">twenty_four</option><option value="custom">custom</option></select></label>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className={`px-2 py-1 rounded-full border ${SHIFT_KIND_STYLES[row.shift_kind] || SHIFT_KIND_STYLES.custom}`}>{row.shift_kind || 'custom'}</span>
                    <span>Limpo: <strong>{row.professional_name_normalized || '—'}</strong></span>
                    <span>Canônico: <strong>{row.canonical_name || '—'}</strong></span>
                    <span>CRM: <strong>{row.crm_detected || '—'}</strong></span>
                    <span>Score: <strong>{Math.round((row.confidence || 0) * 100)}%</strong></span>
                    <span>Status: <strong>{row.match_status}</strong></span>
                    {row._ui_flags?.auto && <span className="px-2 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">Reconhecido automaticamente</span>}
                    {row._ui_flags?.manual && <span className="px-2 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200">Corrigido manualmente</span>}
                    {row._ui_flags?.suggested && <span className="px-2 py-1 rounded-full bg-violet-50 text-violet-700 border border-violet-200">Sugerido por alias/CRM</span>}
                    {row._ui_isAnomalous && <span className="px-2 py-1 rounded-full bg-rose-50 text-rose-700 border border-rose-200">Anomalia detectada</span>}
                  </div>
                  {row._ui_diffItems?.length > 0 && (
                    <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-2 py-1.5">
                      <p className="text-[11px] font-semibold text-amber-800">Diff OCR → edição</p>
                      <ul className="mt-1 space-y-0.5 text-[11px] text-amber-900">
                        {row._ui_diffItems.map((item) => (
                          <li key={`${row.source_row_index}-${item.field}`}>
                            <strong>{item.label}:</strong> <span className="line-through opacity-80">{item.from || '—'}</span> → <span className="font-semibold">{item.to || '—'}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </article>
        )
      })}
    </div>
  )
}

function ReviewPanel({ summary, importDetail, isConfirming, error, onConfirm, onValidate, onReset }) {
  const rows = importDetail?.rows ?? []
  const hasImportable = summary.importable_rows > 0
  const isAlreadyConfirmed = summary.confirmed
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 mb-1">Revisão da importação</h1>
          <p className="text-sm text-gray-500">Arquivo: <span className="font-medium text-gray-700">{summary.filename}</span></p>
        </div>
        <button onClick={onReset} disabled={isConfirming} className="text-sm text-gray-400 hover:text-red-500 transition-colors disabled:opacity-40">✕ Descartar e enviar outro arquivo</button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4"><p className="text-sm font-semibold text-gray-600 mb-3">Resumo da validação</p><SummaryBadges summary={summary} /></div>
      <ErrorMessage message={error} />
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm"><div className="p-4"><ImportRowsTable rows={rows} /></div></div>

      {!isAlreadyConfirmed && <div className="flex flex-wrap items-center gap-3"><button onClick={onValidate} disabled={isConfirming} className="bg-indigo-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">Revalidar staging</button><button onClick={onConfirm} disabled={!hasImportable || isConfirming} className="bg-green-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50">{isConfirming ? 'Confirmando...' : `Confirmar importação (${summary.importable_rows} linhas)`}</button><button onClick={onReset} disabled={isConfirming} className="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-40">Cancelar</button></div>}
    </div>
  )
}

function ConfirmedView({ summary, shiftsCreated, onReset }) {
  return <div className="max-w-lg"><div className="bg-white rounded-xl border border-green-200 shadow-sm p-8 text-center"><div className="text-5xl mb-4">✅</div><h1 className="text-2xl font-bold text-gray-800 mb-2">Importação confirmada</h1><p className="text-gray-600 mb-5">{shiftsCreated !== null ? <><span className="text-3xl font-bold text-green-600">{shiftsCreated}</span> turnos criados.</> : 'Importação concluída.'}</p><div className="flex justify-center"><SummaryBadges summary={summary} /></div><p className="text-xs text-gray-400 mt-4">Confirmado em {fmtDateTime(summary.confirmed_at)}</p><button onClick={onReset} className="mt-6 text-sm text-blue-600 hover:text-blue-700 font-medium">Importar outro arquivo</button></div></div>
}

function groupRowsByDay(rows) {
  return rows.reduce((acc, row) => {
    const key = row.day_group_id || row.date_iso || 'sem-data'
    if (!acc[key]) acc[key] = { dateLabel: row.date_iso || row.date_raw || key, weekday: row.weekday_raw, layoutType: row.source_layout_type || 'generic_table', rows: [], alerts: [] }
    acc[key].rows.push(row)
    const localAlerts = [...(row.grouped_day_validation || []), ...(row.validation_messages || []).filter((m) => /conflito|ambígu|crm|duplicado/i.test(m))]
    acc[key].alerts = Array.from(new Set([...(acc[key].alerts || []), ...localAlerts]))
    return acc
  }, {})
}

function ImportPage() {
  const [pageState, setPageState] = useState(STATE.IDLE)
  const [selectedFile, setSelectedFile] = useState(null)
  const [referencePeriod, setReferencePeriod] = useState('')
  const [sourceDesc, setSourceDesc] = useState('')
  const [summary, setSummary] = useState(null)
  const [importDetail, setImportDetail] = useState(null)
  const [confirmResult, setConfirmResult] = useState(null)
  const [error, setError] = useState('')
  const [ocrPayloadText, setOcrPayloadText] = useState('')
  const [docImportId, setDocImportId] = useState(null)
  const [ocrPreviewRows, setOcrPreviewRows] = useState([])
  const [ocrOriginalRowsByIndex, setOcrOriginalRowsByIndex] = useState({})

  const enhancedOcrPreviewRows = useMemo(() => {
    const anomalyRegex = /conflito|ambígu|crm|duplicado|falt|erro|inconsist/i
    return ocrPreviewRows.map((row) => {
      const rowKey = buildOcrRowKey(row)
      const original = ocrOriginalRowsByIndex[rowKey] || {}
      const diffItems = EDITABLE_OCR_FIELDS
        .filter((field) => (original[field] || '') !== (row[field] || ''))
        .map((field) => ({
          field,
          label: field === 'professional_name_raw' ? 'Nome' : field === 'start_time_raw' ? 'Início' : field === 'end_time_raw' ? 'Fim' : 'Turno',
          from: original[field] || '',
          to: row[field] || '',
        }))
      const suggested = Boolean(row.alias_applied || row.crm_detected || row.suggested_existing_user_id || row.suggested_profile_enrichment)
      const isAnomalous = [...(row.grouped_day_validation || []), ...(row.validation_messages || [])].some((msg) => anomalyRegex.test(msg || ''))
      return {
        ...row,
        _ui_row_key: rowKey,
        _ui_diffItems: diffItems,
        _ui_flags: {
          auto: diffItems.length === 0,
          manual: diffItems.length > 0,
          suggested,
        },
        _ui_isAnomalous: isAnomalous,
      }
    })
  }, [ocrOriginalRowsByIndex, ocrPreviewRows])

  const groupedDays = useMemo(() => {
    const base = groupRowsByDay(enhancedOcrPreviewRows)
    Object.values(base).forEach((day) => { day.overallScore = day.rows.length ? day.rows.reduce((acc, row) => acc + (row.confidence || 0), 0) / day.rows.length : 0 })
    return base
  }, [enhancedOcrPreviewRows])

  const handleFileChange = (e) => setSelectedFile(e.target.files[0] ?? null)

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!selectedFile) return
    setError('')
    setPageState(STATE.UPLOADING)
    const formData = new FormData()
    formData.append('file', selectedFile)
    if (referencePeriod.trim()) formData.append('reference_period', referencePeriod.trim())
    if (sourceDesc.trim()) formData.append('source_description', sourceDesc.trim())
    try {
      const { data: summaryData } = await api.post('/schedule-imports/', formData, { headers: { 'Content-Type': undefined } })
      setSummary(summaryData)
      const { data: detailData } = await api.get(`/schedule-imports/${summaryData.import_id}`)
      setImportDetail(detailData)
      setPageState(STATE.REVIEWING)
    } catch (err) {
      setError(typeof err?.response?.data?.detail === 'string' ? err.response.data.detail : 'Erro ao processar arquivo.')
      setPageState(STATE.IDLE)
    }
  }

  const handleConfirm = async () => {
    setError('')
    setPageState(STATE.CONFIRMING)
    try {
      const { data: result } = await api.post(`/schedule-imports/${summary.import_id}/confirm`)
      setConfirmResult(result)
      setPageState(STATE.CONFIRMED)
    } catch (err) {
      setError(typeof err?.response?.data?.detail === 'string' ? err.response.data.detail : 'Erro ao confirmar importação.')
      setPageState(STATE.REVIEWING)
    }
  }

  const handleValidate = async () => {
    if (!summary?.import_id) return
    setError('')
    setPageState(STATE.CONFIRMING)
    try {
      const { data: summaryData } = await api.post(`/schedule-imports/${summary.import_id}/validate`)
      setSummary(summaryData)
      const { data: detailData } = await api.get(`/schedule-imports/${summary.import_id}`)
      setImportDetail(detailData)
      setPageState(STATE.REVIEWING)
    } catch (err) {
      setError(typeof err?.response?.data?.detail === 'string' ? err.response.data.detail : 'Erro ao revalidar staging.')
      setPageState(STATE.REVIEWING)
    }
  }

  const handleReset = () => {
    setPageState(STATE.IDLE)
    setSelectedFile(null)
    setReferencePeriod('')
    setSourceDesc('')
    setSummary(null)
    setImportDetail(null)
    setConfirmResult(null)
    setDocImportId(null)
    setOcrPayloadText('')
    setOcrPreviewRows([])
    setOcrOriginalRowsByIndex({})
    setError('')
  }

  const handleParseOcrPayload = async () => {
    setError('')
    setPageState(STATE.UPLOADING)
    try {
      const payload = JSON.parse(ocrPayloadText || '{}')
      const { data: parsed } = await api.post('/admin/imports/parse-ocr-payload', { source_filename: 'debug_ocr_payload.json', payload })
      setDocImportId(parsed.document_import_id)
      const { data: preview } = await api.get(`/admin/imports/${parsed.document_import_id}/normalized-preview`)
      const rows = preview.rows || []
      setOcrOriginalRowsByIndex(Object.fromEntries(rows.map((row) => [buildOcrRowKey(row), { ...row }])))
      setOcrPreviewRows(rows)
      setPageState(STATE.IDLE)
    } catch (err) {
      setError(typeof err?.response?.data?.detail === 'string' ? err.response.data.detail : 'Falha ao processar payload OCR.')
      setPageState(STATE.IDLE)
    }
  }

  const applyOcrToStaging = async () => {
    if (!docImportId) return
    setPageState(STATE.UPLOADING)
    try {
      const editedRows = ocrPreviewRows.map((row) => ({
        source_row_index: row.source_row_index,
        source_row_key: buildOcrRowKey(row),
        professional_name_raw: row.professional_name_raw,
        professional_name_normalized: row.professional_name_normalized,
        canonical_name: row.canonical_name,
        start_time_raw: row.start_time_raw,
        end_time_raw: row.end_time_raw,
        shift_kind: row.shift_kind,
        crm_detected: row.crm_detected,
        matched_user_id: row.matched_user_id,
        suggested_existing_user_id: row.suggested_existing_user_id,
      }))
      const { data: applyResult } = await api.post(`/admin/imports/${docImportId}/apply-to-staging`, { edited_rows: editedRows })
      const { data: summaryData } = await api.get(`/schedule-imports/${applyResult.schedule_import_id}/summary`)
      const { data: detailData } = await api.get(`/schedule-imports/${applyResult.schedule_import_id}`)
      setSummary(summaryData)
      setImportDetail(detailData)
      setPageState(STATE.REVIEWING)
    } catch (err) {
      setError(typeof err?.response?.data?.detail === 'string' ? err.response.data.detail : 'Falha ao aplicar OCR ao staging.')
      setPageState(STATE.IDLE)
    }
  }

  const onInlineEdit = (rowKey, field, value) => {
    setOcrPreviewRows((current) => current.map((row) => (buildOcrRowKey(row) === rowKey ? { ...row, [field]: value } : row)))
  }

  if (pageState === STATE.CONFIRMED) return <ConfirmedView summary={confirmResult} shiftsCreated={extractShiftsCreated(confirmResult)} onReset={handleReset} />
  if (pageState === STATE.REVIEWING || pageState === STATE.CONFIRMING) return <ReviewPanel summary={summary} importDetail={importDetail} isConfirming={pageState === STATE.CONFIRMING} error={error} onConfirm={handleConfirm} onValidate={handleValidate} onReset={handleReset} />

  return (
    <div className="space-y-6">
      <UploadForm selectedFile={selectedFile} referencePeriod={referencePeriod} sourceDescription={sourceDesc} isUploading={pageState === STATE.UPLOADING} error={error} onFileChange={handleFileChange} onReferencePeriodChange={(e) => setReferencePeriod(e.target.value)} onSourceDescriptionChange={(e) => setSourceDesc(e.target.value)} onSubmit={handleUpload} />

      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Debug OCR (payload JSON)</h3>
        <p className="text-xs text-gray-500 mb-2">Parser determinístico local + fallback opcional. {docImportId ? `document_import_id: ${docImportId}` : ''}</p>
        <textarea value={ocrPayloadText} onChange={(e) => setOcrPayloadText(e.target.value)} placeholder='{"pages":[{"page_number":1,"tables":[{"title":"MARÇO/2026","headers":["Profissional","Data","Entrada","Saída"],"rows":[["Maria","01/03/2026","08:00","20:00"]]}]}]}' className="w-full min-h-40 border border-gray-300 rounded-lg px-3 py-2 text-xs font-mono" />
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" onClick={handleParseOcrPayload} disabled={pageState === STATE.UPLOADING || !ocrPayloadText.trim()} className="bg-slate-700 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50">1) Parse + Preview OCR</button>
          <button type="button" onClick={applyOcrToStaging} disabled={!docImportId || pageState === STATE.UPLOADING} className="bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50">2) Apply to staging</button>
        </div>
      </div>

      {ocrPreviewRows.length > 0 && (
        <section className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
          <OcrDayCards groupedDays={groupedDays} onInlineEdit={onInlineEdit} />
          <div className="lg:sticky lg:top-4"><OcrSideSummary groupedDays={groupedDays} /></div>
        </section>
      )}
    </div>
  )
}

export default ImportPage

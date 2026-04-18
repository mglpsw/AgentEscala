import { useState } from 'react'
import api from '../api/client.js'
import ImportRowsTable from '../components/import_rows_table.jsx'

// Estados internos da máquina de estados da página
const STATE = {
  IDLE:       'idle',       // aguardando upload
  UPLOADING:  'uploading',  // enviando arquivo para o backend
  REVIEWING:  'reviewing',  // exibindo staging para revisão do admin
  CONFIRMING: 'confirming', // aguardando resposta do confirm
  CONFIRMED:  'confirmed',  // importação confirmada com sucesso
}

// Extrai o número de turnos criados da nota injetada pelo backend no source_description
// O backend adiciona: "[Turnos criados nesta confirmação: N]" ao campo
function extractShiftsCreated(summary) {
  const match = summary?.source_description?.match(/Turnos criados nesta confirmação:\s*(\d+)/)
  return match ? parseInt(match[1], 10) : null
}

// Formata datetime ISO para exibição local em pt-BR
function fmtDateTime(dt) {
  if (!dt) return '—'
  try {
    return new Date(dt).toLocaleString('pt-BR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return String(dt)
  }
}

// Mensagem de erro inline reutilizável
function ErrorMessage({ message }) {
  if (!message) return null
  return (
    <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
      {message}
    </p>
  )
}

// Badges coloridos com os contadores do resumo da importação
function SummaryBadges({ summary }) {
  const items = [
    { label: 'Total',       value: summary.total_rows,      cls: 'bg-gray-100 text-gray-700'     },
    { label: 'Válidas',     value: summary.valid_rows,      cls: 'bg-green-100 text-green-800'   },
    { label: 'Alertas',     value: summary.warning_rows,    cls: 'bg-yellow-100 text-yellow-800' },
    { label: 'Erros',       value: summary.invalid_rows,    cls: 'bg-red-100 text-red-800'       },
    { label: 'Duplicatas',  value: summary.duplicate_rows,  cls: 'bg-purple-100 text-purple-800' },
    { label: 'Importáveis', value: summary.importable_rows, cls: 'bg-blue-100 text-blue-800'     },
  ]
  return (
    <div className="flex flex-wrap gap-2">
      {items.map(({ label, value, cls }) => (
        <span key={label} className={`px-3 py-1 rounded-full text-sm font-semibold ${cls}`}>
          {label}: {value}
        </span>
      ))}
    </div>
  )
}

// ─── Formulário de upload ──────────────────────────────────────────────────────

function UploadForm({
  selectedFile, referencePeriod, sourceDescription, isUploading, error,
  onFileChange, onReferencePeriodChange, onSourceDescriptionChange, onSubmit,
}) {
  return (
    <div className="max-w-xl">

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-1">Importar Escala</h1>
        <p className="text-sm text-gray-500">
          Envie um arquivo CSV ou XLSX com os turnos da escala. O sistema valida as linhas e exibe
          um resumo antes de criar os turnos definitivamente.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h2 className="text-base font-semibold text-gray-700 mb-4">Selecionar arquivo</h2>

        <form onSubmit={onSubmit} className="space-y-4">

          <div>
            <label htmlFor="import-file" className="block text-sm font-medium text-gray-700 mb-1">
              Arquivo <span className="text-red-500">*</span>
            </label>
            <input
              id="import-file"
              type="file"
              accept=".csv,.xlsx,.xls,.pdf,.png,.jpg,.jpeg,.webp,.tiff"
              required
              onChange={onFileChange}
              className="block w-full text-sm text-gray-700
                file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0
                file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100 cursor-pointer"
            />
            <p className="text-xs text-gray-400 mt-1">
              Formatos aceitos: .csv, .xlsx, .pdf e imagens (.png/.jpg/.webp/.tiff)
            </p>
          </div>

          <div>
            <label htmlFor="reference-period" className="block text-sm font-medium text-gray-700 mb-1">
              Período de referência{' '}
              <span className="text-gray-400 font-normal">(opcional)</span>
            </label>
            <input
              id="reference-period"
              type="text"
              value={referencePeriod}
              onChange={onReferencePeriodChange}
              placeholder="Ex.: 2026-03"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label htmlFor="source-desc" className="block text-sm font-medium text-gray-700 mb-1">
              Descrição da origem{' '}
              <span className="text-gray-400 font-normal">(opcional)</span>
            </label>
            <input
              id="source-desc"
              type="text"
              value={sourceDescription}
              onChange={onSourceDescriptionChange}
              placeholder="Ex.: Escala março do setor A"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <ErrorMessage message={error} />

          <button
            type="submit"
            disabled={!selectedFile || isUploading}
            className="w-full bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium
              hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isUploading ? 'Processando...' : 'Enviar e validar'}
          </button>

        </form>
      </div>

      {/* Instruções de formato */}
      <div className="mt-4 bg-blue-50 border border-blue-100 rounded-lg px-4 py-3">
        <p className="text-xs text-blue-700 font-medium mb-1">Como preparar o arquivo</p>
        <ul className="text-xs text-blue-600 space-y-0.5 list-disc list-inside">
          <li>Colunas obrigatórias: profissional, data, hora_inicio, hora_fim</li>
          <li>Colunas opcionais: total_horas, observacoes, origem</li>
          <li>Datas: DD/MM/YYYY ou YYYY-MM-DD. Horários: HH:MM</li>
          <li>Após envio, revise as linhas antes de confirmar a importação</li>
          <li>Somente linhas válidas e de alerta (não duplicadas) são criadas como turnos</li>
        </ul>
      </div>

    </div>
  )
}

// ─── Painel de revisão do staging ─────────────────────────────────────────────

function ReviewPanel({ summary, importDetail, isConfirming, error, onConfirm, onValidate, onReset }) {
  const rows = importDetail?.rows ?? []
  const invalidCount = rows.filter((row) => row.row_status === 'invalid').length
  const ambiguousCount = rows.filter((row) => row.match_status?.includes('ambiguous')).length
  const conflictCount = rows.filter((row) => row.validation_status === 'conflict' || row.has_overlap).length
  const hasImportable = summary.importable_rows > 0
  const isAlreadyConfirmed = summary.confirmed

  return (
    <div className="space-y-6">

      {/* Cabeçalho com nome do arquivo e botão de descarte */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 mb-1">Revisão da importação</h1>
          <p className="text-sm text-gray-500">
            Arquivo: <span className="font-medium text-gray-700">{summary.filename}</span>
            {summary.reference_period && (
              <> &nbsp;·&nbsp; Período:{' '}
                <span className="font-medium text-gray-700">{summary.reference_period}</span>
              </>
            )}
          </p>
        </div>
        <button
          onClick={onReset}
          disabled={isConfirming}
          className="text-sm text-gray-400 hover:text-red-500 transition-colors disabled:opacity-40"
        >
          ✕ Descartar e enviar outro arquivo
        </button>
      </div>

      {/* Resumo dos contadores de validação */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
        <p className="text-sm font-semibold text-gray-600 mb-3">Resumo da validação</p>
        <SummaryBadges summary={summary} />
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <span className="px-2 py-1 rounded bg-red-50 text-red-700">Inválidas: {invalidCount}</span>
          <span className="px-2 py-1 rounded bg-rose-50 text-rose-700">Ambíguas: {ambiguousCount}</span>
          <span className="px-2 py-1 rounded bg-orange-50 text-orange-700">Conflitos: {conflictCount}</span>
        </div>

        {!hasImportable && !isAlreadyConfirmed && (
          <p className="mt-3 text-sm text-red-600 bg-red-50 border border-red-100 rounded px-3 py-2">
            Nenhuma linha importável encontrada. Corrija o arquivo e envie novamente.
          </p>
        )}

        {isAlreadyConfirmed && (
          <p className="mt-3 text-sm text-green-700 bg-green-50 border border-green-100 rounded px-3 py-2">
            Esta importação já foi confirmada em {fmtDateTime(summary.confirmed_at)}.
          </p>
        )}
      </div>

      <ErrorMessage message={error} />

      {/* Tabela de linhas do staging */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between flex-wrap gap-2">
          <p className="text-sm font-semibold text-gray-700">
            Linhas do staging ({rows.length})
          </p>
          {/* Legenda de cores */}
          <div className="flex gap-3 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-green-400 inline-block" /> válida
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-yellow-400 inline-block" /> alerta
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-red-400 inline-block" /> erro
            </span>
          </div>
        </div>
        <div className="p-4">
          <ImportRowsTable rows={rows} />
        </div>
      </div>

      {/* Ação de confirmação — oculta se já confirmado */}
      {!isAlreadyConfirmed && (
        <div className="flex items-center gap-4">
          <button
            onClick={onValidate}
            disabled={isConfirming}
            className="bg-indigo-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium
              hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Revalidar staging
          </button>
          <button
            onClick={onConfirm}
            disabled={!hasImportable || isConfirming}
            className="bg-green-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium
              hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isConfirming
              ? 'Confirmando...'
              : `Confirmar importação (${summary.importable_rows} linhas)`}
          </button>
          <button
            onClick={onReset}
            disabled={isConfirming}
            className="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-40 transition-colors"
          >
            Cancelar
          </button>
        </div>
      )}

    </div>
  )
}

// ─── Tela de sucesso ───────────────────────────────────────────────────────────

function ConfirmedView({ summary, shiftsCreated, onReset }) {
  return (
    <div className="max-w-lg">
      <div className="bg-white rounded-xl border border-green-200 shadow-sm p-8 text-center">

        <div className="text-5xl mb-4">✅</div>
        <h1 className="text-2xl font-bold text-gray-800 mb-2">Importação confirmada</h1>

        {shiftsCreated !== null ? (
          <p className="text-gray-600 mb-5">
            <span className="text-3xl font-bold text-green-600">{shiftsCreated}</span>{' '}
            {shiftsCreated === 1 ? 'turno criado' : 'turnos criados'} com sucesso.
          </p>
        ) : (
          <p className="text-gray-500 mb-5">
            Importação concluída. Verifique os turnos no calendário.
          </p>
        )}

        <div className="flex justify-center">
          <SummaryBadges summary={summary} />
        </div>

        <p className="text-xs text-gray-400 mt-4">
          Confirmado em {fmtDateTime(summary.confirmed_at)}
        </p>

        <button
          onClick={onReset}
          className="mt-6 text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
        >
          Importar outro arquivo
        </button>

      </div>
    </div>
  )
}

// ─── Página principal ──────────────────────────────────────────────────────────

function ImportPage() {
  const [pageState,        setPageState]        = useState(STATE.IDLE)
  const [selectedFile,     setSelectedFile]     = useState(null)
  const [referencePeriod,  setReferencePeriod]  = useState('')
  const [sourceDesc,       setSourceDesc]       = useState('')
  const [summary,          setSummary]          = useState(null)   // ScheduleImportSummary
  const [importDetail,     setImportDetail]     = useState(null)   // ScheduleImportDetailResponse
  const [confirmResult,    setConfirmResult]    = useState(null)   // ScheduleImportSummary pós-confirm
  const [error,            setError]            = useState('')
  const [ocrPayloadText,   setOcrPayloadText]   = useState('')
  const [docImportId,      setDocImportId]      = useState(null)

  const handleFileChange = (e) => setSelectedFile(e.target.files[0] ?? null)

  // Envia o arquivo para POST /schedule-imports/ e carrega o staging
  const handleUpload = async (e) => {
    e.preventDefault()
    if (!selectedFile) return

    setError('')
    setPageState(STATE.UPLOADING)

    // FormData sem Content-Type manual — o browser define multipart/form-data com boundary correto
    const formData = new FormData()
    formData.append('file', selectedFile)
    if (referencePeriod.trim()) formData.append('reference_period', referencePeriod.trim())
    if (sourceDesc.trim())      formData.append('source_description', sourceDesc.trim())

    try {
      const { data: summaryData } = await api.post('/schedule-imports/', formData, {
        headers: { 'Content-Type': undefined },
      })
      setSummary(summaryData)

      // Busca o detalhe completo com as linhas do staging para exibição
      const { data: detailData } = await api.get(`/schedule-imports/${summaryData.import_id}`)
      setImportDetail(detailData)
      setPageState(STATE.REVIEWING)
    } catch (err) {
      const detail = err?.response?.data?.detail
      const msg = typeof detail === 'string'
        ? detail
        : 'Erro ao processar o arquivo. Verifique o formato e tente novamente.'
      setError(msg)
      setPageState(STATE.IDLE)
    }
  }

  // Confirma a importação via POST /schedule-imports/{id}/confirm — cria os turnos reais
  const handleConfirm = async () => {
    setError('')
    setPageState(STATE.CONFIRMING)

    try {
      const { data: result } = await api.post(`/schedule-imports/${summary.import_id}/confirm`)
      setConfirmResult(result)
      setPageState(STATE.CONFIRMED)
    } catch (err) {
      const detail = err?.response?.data?.detail
      const msg = typeof detail === 'string'
        ? detail
        : 'Erro ao confirmar a importação. Tente novamente.'
      setError(msg)
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
      const detail = err?.response?.data?.detail
      const msg = typeof detail === 'string' ? detail : 'Erro ao revalidar o staging.'
      setError(msg)
      setPageState(STATE.REVIEWING)
    }
  }

  // Descarta o staging e volta ao estado inicial para novo upload
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
    setError('')
  }

  const handleParseOcrPayload = async () => {
    setError('')
    setPageState(STATE.UPLOADING)
    try {
      const payload = JSON.parse(ocrPayloadText || '{}')
      const { data: parsed } = await api.post('/admin/imports/parse-ocr-payload', {
        source_filename: 'debug_ocr_payload.json',
        payload,
      })
      setDocImportId(parsed.document_import_id)
      const { data: applyResult } = await api.post(`/admin/imports/${parsed.document_import_id}/apply-to-staging`)
      const { data: summaryData } = await api.get(`/schedule-imports/${applyResult.schedule_import_id}/summary`)
      const { data: detailData } = await api.get(`/schedule-imports/${applyResult.schedule_import_id}`)
      setSummary(summaryData)
      setImportDetail(detailData)
      setPageState(STATE.REVIEWING)
    } catch (err) {
      const detail = err?.response?.data?.detail
      const msg = typeof detail === 'string' ? detail : 'Falha ao processar payload OCR.'
      setError(msg)
      setPageState(STATE.IDLE)
    }
  }

  // Tela de sucesso após confirmação bem-sucedida
  if (pageState === STATE.CONFIRMED) {
    return (
      <ConfirmedView
        summary={confirmResult}
        shiftsCreated={extractShiftsCreated(confirmResult)}
        onReset={handleReset}
      />
    )
  }

  // Painel de revisão do staging após upload
  if (pageState === STATE.REVIEWING || pageState === STATE.CONFIRMING) {
    return (
      <ReviewPanel
        summary={summary}
        importDetail={importDetail}
        isConfirming={pageState === STATE.CONFIRMING}
        error={error}
        onConfirm={handleConfirm}
        onValidate={handleValidate}
        onReset={handleReset}
      />
    )
  }

  // Formulário de upload (estado inicial)
  return (
    <div className="space-y-6">
      <UploadForm
        selectedFile={selectedFile}
        referencePeriod={referencePeriod}
        sourceDescription={sourceDesc}
        isUploading={pageState === STATE.UPLOADING}
        error={error}
        onFileChange={handleFileChange}
        onReferencePeriodChange={(e) => setReferencePeriod(e.target.value)}
        onSourceDescriptionChange={(e) => setSourceDesc(e.target.value)}
        onSubmit={handleUpload}
      />
      <div className="bg-white border border-gray-200 rounded-xl p-4 max-w-3xl">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Debug OCR (payload JSON)</h3>
        <p className="text-xs text-gray-500 mb-2">
          Fluxo conservador: parse-documento normalizado → apply-to-staging → revisão humana.
          {docImportId ? ` Último document_import_id: ${docImportId}` : ''}
        </p>
        <textarea
          value={ocrPayloadText}
          onChange={(e) => setOcrPayloadText(e.target.value)}
          placeholder='{"pages":[{"page_number":1,"tables":[{"title":"MARÇO/2026","headers":["Profissional","Data","Entrada","Saída"],"rows":[["Maria","01/03/2026","08:00","20:00"]]}]}]}'
          className="w-full min-h-40 border border-gray-300 rounded-lg px-3 py-2 text-xs font-mono"
        />
        <button
          type="button"
          onClick={handleParseOcrPayload}
          disabled={pageState === STATE.UPLOADING || !ocrPayloadText.trim()}
          className="mt-3 bg-slate-700 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
        >
          Processar payload OCR e enviar ao staging
        </button>
      </div>
    </div>
  )
}

export default ImportPage

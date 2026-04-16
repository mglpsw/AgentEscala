import api from './client.js'

const DEFAULT_FINAL_SCHEDULE_FILENAME = 'escala_final.xlsx'

export async function fetchFinalScheduleRows(params = {}) {
  const { data } = await api.get('/shifts/final-schedule', { params })
  return data
}

export async function downloadFinalScheduleExport(params = {}) {
  const response = await api.get('/shifts/export', {
    params: { ...params, format: 'xlsx', view: 'essential' },
    responseType: 'blob',
  })
  const filename = getFilenameFromContentDisposition(
    response.headers?.['content-disposition'],
    DEFAULT_FINAL_SCHEDULE_FILENAME,
  )

  triggerBlobDownload(response.data, filename)
  return { filename, blob: response.data }
}

export function getFilenameFromContentDisposition(contentDisposition, fallback) {
  if (!contentDisposition) return fallback

  const encodedFilename = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (encodedFilename?.[1]) {
    try {
      return decodeURIComponent(encodedFilename[1].trim().replace(/^"|"$/g, ''))
    } catch {
      return encodedFilename[1].trim().replace(/^"|"$/g, '') || fallback
    }
  }

  const filename = contentDisposition.match(/filename="?([^";]+)"?/i)
  return filename?.[1]?.trim() || fallback
}

function triggerBlobDownload(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = url
  link.download = filename
  link.style.display = 'none'

  document.body.appendChild(link)
  link.click()
  link.remove()

  window.setTimeout(() => window.URL.revokeObjectURL(url), 0)
}

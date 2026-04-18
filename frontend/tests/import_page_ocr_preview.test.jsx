import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ImportPage from '../src/pages/import_page.jsx'
import api from '../src/api/client.js'

vi.mock('../src/api/client.js', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}))

describe('ImportPage OCR preview agrupada por dia', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('agrupa preview OCR por dia e exibe resumo lateral', async () => {
    api.post.mockResolvedValueOnce({ data: { document_import_id: 'abc-1' } })
    api.get.mockResolvedValueOnce({
      data: {
        rows: [
          {
            source_row_index: 1,
            day_group_id: '2026-04-10',
            date_iso: '2026-04-10',
            weekday_raw: 'SEX',
            source_layout_type: 'pa24h_block',
            professional_name_raw: 'LETICIA E JEAN',
            professional_name_normalized: 'Leticia',
            canonical_name: 'Leticia Leonarda',
            shift_kind: 'day',
            confidence: 0.92,
            match_status: 'ambiguous',
            grouped_day_validation: ['Nome ambíguo'],
            validation_messages: ['CRM ausente'],
          },
        ],
      },
    })

    render(<ImportPage />)

    fireEvent.change(screen.getByPlaceholderText(/{"pages":/i), {
      target: {
        value: JSON.stringify({ pages: [{ page_number: 1, tables: [] }] }),
      },
    })
    fireEvent.click(screen.getByRole('button', { name: /parse \+ preview ocr/i }))

    await waitFor(() => {
      expect(screen.getByText(/layout: pa24h_block/i)).toBeInTheDocument()
    })

    expect(screen.getByText(/Resumo OCR por dia/i)).toBeInTheDocument()
    expect(screen.getByText(/Linhas ambíguas/i)).toBeInTheDocument()
    expect(screen.getByDisplayValue('LETICIA E JEAN')).toBeInTheDocument()
  })
})

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

  it('envia edições inline no apply-to-staging', async () => {
    api.post
      .mockResolvedValueOnce({ data: { document_import_id: 'abc-2' } })
      .mockResolvedValueOnce({ data: { schedule_import_id: 77 } })
    api.get
      .mockResolvedValueOnce({
        data: {
          rows: [
            {
              source_row_index: 22,
              day_group_id: '2026-04-11',
              date_iso: '2026-04-11',
              source_layout_type: 'generic_table',
              professional_name_raw: 'NOME ORIGINAL',
              professional_name_normalized: 'Nome Original',
              canonical_name: 'Nome Original',
              start_time_raw: '08:00',
              end_time_raw: '20:00',
              shift_kind: 'day',
              confidence: 0.9,
              match_status: 'matched',
              alias_applied: true,
              validation_messages: ['Possível conflito de CRM'],
            },
          ],
        },
      })
      .mockResolvedValueOnce({ data: { import_id: 77, total_rows: 1, valid_rows: 1, warning_rows: 0, invalid_rows: 0, duplicate_rows: 0, importable_rows: 1 } })
      .mockResolvedValueOnce({ data: { rows: [] } })

    render(<ImportPage />)
    fireEvent.change(screen.getByPlaceholderText(/{"pages":/i), {
      target: { value: JSON.stringify({ pages: [{ page_number: 1, tables: [] }] }) },
    })
    fireEvent.click(screen.getByRole('button', { name: /parse \+ preview ocr/i }))
    await waitFor(() => expect(screen.getByDisplayValue('NOME ORIGINAL')).toBeInTheDocument())

    fireEvent.change(screen.getByDisplayValue('NOME ORIGINAL'), { target: { value: 'NOME EDITADO' } })
    expect(screen.getByText(/sugerido por alias\/crm/i)).toBeInTheDocument()
    expect(screen.getByText(/anomalia detectada/i)).toBeInTheDocument()
    expect(screen.getByText(/diff ocr → edição/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /apply to staging/i }))

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/admin/imports/abc-2/apply-to-staging',
        expect.objectContaining({
          edited_rows: expect.arrayContaining([
            expect.objectContaining({
              source_row_index: 22,
              source_row_key: expect.any(String),
              professional_name_raw: 'NOME EDITADO',
            }),
          ]),
        }),
      )
    })
  })

  it('edita apenas a linha alvo quando source_row_index se repete entre páginas', async () => {
    api.post.mockResolvedValueOnce({ data: { document_import_id: 'abc-3' } })
    api.get.mockResolvedValueOnce({
      data: {
        rows: [
          {
            source_page: 1,
            source_row_index: 1,
            day_group_id: '2026-04-12',
            date_iso: '2026-04-12',
            source_layout_type: 'generic_table',
            professional_name_raw: 'DUPLICADO P1',
            start_time_raw: '08:00',
            end_time_raw: '20:00',
            shift_kind: 'day',
            confidence: 0.9,
            match_status: 'matched',
          },
          {
            source_page: 2,
            source_row_index: 1,
            day_group_id: '2026-04-12',
            date_iso: '2026-04-12',
            source_layout_type: 'generic_table',
            professional_name_raw: 'DUPLICADO P2',
            start_time_raw: '08:00',
            end_time_raw: '20:00',
            shift_kind: 'day',
            confidence: 0.9,
            match_status: 'matched',
          },
        ],
      },
    })

    render(<ImportPage />)
    fireEvent.change(screen.getByPlaceholderText(/{"pages":/i), {
      target: { value: JSON.stringify({ pages: [{ page_number: 1, tables: [] }] }) },
    })
    fireEvent.click(screen.getByRole('button', { name: /parse \+ preview ocr/i }))
    await waitFor(() => expect(screen.getByDisplayValue('DUPLICADO P1')).toBeInTheDocument())

    fireEvent.change(screen.getByDisplayValue('DUPLICADO P2'), { target: { value: 'DUPLICADO P2 EDITADO' } })

    expect(screen.getByDisplayValue('DUPLICADO P1')).toBeInTheDocument()
    expect(screen.getByDisplayValue('DUPLICADO P2 EDITADO')).toBeInTheDocument()
  })
})

import React, { useEffect, useState, useCallback } from 'react'
import api from '../api/client.js'
import PendingSwapCard from '../components/pending_swap_card.jsx'

function PendingSwapsPage() {
  const [swaps, setSwaps] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionId, setActionId] = useState(null) // id da troca em ação
  const [success, setSuccess] = useState('')

  const fetchSwaps = useCallback(() => {
    setLoading(true)
    setError('')
    api.get('/swaps/pending')
      .then(res => setSwaps(res.data))
      .catch(() => setError('Erro ao carregar trocas pendentes'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetchSwaps()
  }, [fetchSwaps])

  const handleApprove = async (swapId, obs) => {
    setActionId(swapId)
    setSuccess('')
    try {
      await api.post(`/swaps/${swapId}/approve`, { admin_notes: obs || undefined })
      setSuccess('Troca aprovada com sucesso!')
      fetchSwaps()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Erro ao aprovar troca')
    } finally {
      setActionId(null)
    }
  }

  const handleReject = async (swapId, obs) => {
    setActionId(swapId)
    setSuccess('')
    try {
      await api.post(`/swaps/${swapId}/reject`, { admin_notes: obs || undefined })
      setSuccess('Troca rejeitada com sucesso!')
      fetchSwaps()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Erro ao rejeitar troca')
    } finally {
      setActionId(null)
    }
  }

  return (
    <div className="max-w-2xl mx-auto py-6 px-2 md:px-0">
      <h1 className="text-2xl font-bold mb-1">Trocas Pendentes</h1>
      <div className="text-gray-600 mb-6">Aprovação e rejeição de solicitações de troca de plantão. Apenas administradores podem acessar esta tela.</div>

      {success && <div className="text-green-600 mb-3">{success}</div>}
      {loading && <div className="text-gray-500">Carregando...</div>}
      {error && <div className="text-red-600 mb-2">{error}</div>}
      {!loading && !error && swaps.length === 0 && (
        <div className="text-gray-400">Nenhuma solicitação pendente encontrada.</div>
      )}
      <div className="flex flex-col gap-2">
        {swaps.map(swap => (
          <PendingSwapCard
            key={swap.id}
            swap={swap}
            onApprove={handleApprove}
            onReject={handleReject}
            loading={actionId === swap.id}
          />
        ))}
      </div>
    </div>
  )
}

export default PendingSwapsPage

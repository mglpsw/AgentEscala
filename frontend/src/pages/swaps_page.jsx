import React, { useEffect, useState, useCallback } from 'react'
import api from '../api/client.js'
import useAuth from '../hooks/use_auth.js'
import SwapCard from '../components/swap_card.jsx'
import SwapForm from '../components/swap_form.jsx'

function SwapsPage() {
  const { user } = useAuth()
  const [swaps, setSwaps] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshFlag, setRefreshFlag] = useState(0)
  const [cancelingId, setCancelingId] = useState(null)

  const fetchSwaps = useCallback(() => {
    setLoading(true)
    setError('')
    api.get('/swaps')
      .then(res => setSwaps(res.data))
      .catch(() => setError('Erro ao carregar trocas'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetchSwaps()
    // eslint-disable-next-line
  }, [refreshFlag])

  const handleCreated = () => setRefreshFlag(f => f + 1)

  const handleCancel = async (swapId) => {
    setCancelingId(swapId)
    try {
      await api.post(`/swaps/${swapId}/cancel`)
      setRefreshFlag(f => f + 1)
    } catch {
      alert('Erro ao cancelar solicitação')
    } finally {
      setCancelingId(null)
    }
  }

  return (
    <div className="max-w-2xl mx-auto py-6 px-2 md:px-0">
      <h1 className="text-2xl font-bold mb-1">Trocas de Plantão</h1>
      <div className="text-gray-600 mb-6">Solicite e acompanhe suas trocas de plantão. Apenas solicitações pendentes podem ser canceladas.</div>

      <SwapForm onCreated={handleCreated} />

      <div className="font-semibold mb-2">Suas solicitações de troca</div>
      {loading && <div className="text-gray-500">Carregando...</div>}
      {error && <div className="text-red-600">{error}</div>}
      {!loading && !error && swaps.length === 0 && (
        <div className="text-gray-400">Nenhuma solicitação de troca encontrada.</div>
      )}
      <div className="flex flex-col gap-2">
        {swaps.map(swap => (
          <SwapCard
            key={swap.id}
            swap={swap}
            isCancellable={swap.status === 'pending' && swap.requester_id === user?.id}
            onCancel={handleCancel}
            canceling={cancelingId === swap.id}
          />
        ))}
      </div>
    </div>
  )
}

export default SwapsPage

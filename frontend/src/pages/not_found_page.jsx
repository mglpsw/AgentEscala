import { Link } from 'react-router-dom'

// Página 404 para rotas inexistentes
function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full py-24 text-center">
      <h1 className="text-6xl font-bold text-gray-300 mb-4">404</h1>
      <h2 className="text-2xl font-semibold text-gray-700 mb-2">Página não encontrada</h2>
      <p className="text-gray-500 mb-8">A rota acessada não existe no sistema.</p>
      <Link
        to="/calendar"
        className="bg-blue-600 text-white px-5 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
      >
        Voltar ao início
      </Link>
    </div>
  )
}

export default NotFoundPage

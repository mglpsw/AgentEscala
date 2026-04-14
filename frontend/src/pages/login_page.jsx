import PagePlaceholder from '../components/page_placeholder.jsx'

// Página de login — autenticação JWT será implementada na etapa E5
function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-xl shadow-md p-10 w-full max-w-sm text-center">
        <h2 className="text-2xl font-bold text-blue-700 mb-2">AgentEscala</h2>
        <p className="text-gray-500 text-sm mb-6">Gestão de escalas médicas</p>
        <PagePlaceholder
          title="Login"
          description="Formulário de autenticação JWT será implementado na etapa E5."
        />
      </div>
    </div>
  )
}

export default LoginPage

import PropTypes from 'prop-types'

// Componente reutilizável para páginas ainda não implementadas
function PagePlaceholder({ title, description }) {
  return (
    <div className="flex flex-col items-center justify-center h-full py-24 text-center">
      <h1 className="text-3xl font-bold text-gray-800 mb-3">{title}</h1>
      <p className="text-gray-500 mb-6 max-w-md">{description}</p>
      <span className="inline-block bg-yellow-100 text-yellow-800 text-sm font-medium px-4 py-1.5 rounded-full">
        🚧 Integração prevista nas próximas etapas
      </span>
    </div>
  )
}

export default PagePlaceholder

PagePlaceholder.propTypes = {
  title: PropTypes.string.isRequired,
  description: PropTypes.string.isRequired,
}

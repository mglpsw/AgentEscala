import { useEffect, useMemo, useState } from 'react'
import api from '../api/client.js'

const ROLE_OPTIONS = ['admin', 'medico', 'financeiro']

const initialForm = {
  name: '',
  email: '',
  password: '',
  role: 'medico',
  is_active: true,
}

function UsersAdminPage() {
  const [users, setUsers] = useState([])
  const [form, setForm] = useState(initialForm)
  const [editingUserId, setEditingUserId] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  const isEditing = useMemo(() => editingUserId !== null, [editingUserId])

  const loadUsers = async () => {
    setIsLoading(true)
    setError('')
    try {
      const { data } = await api.get('/admin/users')
      setUsers(data)
    } catch {
      setError('Não foi possível carregar usuários.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  const resetForm = () => {
    setForm(initialForm)
    setEditingUserId(null)
  }

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const startEdit = (user) => {
    setEditingUserId(user.id)
    setForm({
      name: user.name,
      email: user.email,
      password: '',
      role: user.role,
      is_active: user.is_active,
    })
    setError('')
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      if (isEditing) {
        const payload = {
          name: form.name,
          email: form.email,
          role: form.role,
          is_active: form.is_active,
        }

        if (form.password.trim()) {
          payload.password = form.password
        }

        await api.put(`/admin/users/${editingUserId}`, payload)
      } else {
        await api.post('/admin/users', form)
      }

      await loadUsers()
      resetForm()
    } catch (err) {
      if (err?.response?.status === 409) {
        setError('E-mail já cadastrado.')
      } else {
        setError('Não foi possível salvar o usuário.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (userId) => {
    setError('')
    try {
      await api.delete(`/admin/users/${userId}`)
      await loadUsers()
    } catch (err) {
      if (err?.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('Não foi possível excluir o usuário.')
      }
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-gray-900">Administração de Usuários</h2>
        <p className="text-sm text-gray-600 mt-1">CRUD simples de usuários com controle de role.</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white border border-gray-200 rounded-xl p-4 space-y-4">
        <h3 className="font-semibold text-gray-800">{isEditing ? 'Editar usuário' : 'Novo usuário'}</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            required
            type="text"
            placeholder="Nome"
            value={form.name}
            onChange={(e) => handleChange('name', e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <input
            required
            type="email"
            placeholder="E-mail"
            value={form.email}
            onChange={(e) => handleChange('email', e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <input
            type="password"
            required={!isEditing}
            minLength={6}
            placeholder={isEditing ? 'Nova senha (opcional)' : 'Senha'}
            value={form.password}
            onChange={(e) => handleChange('password', e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <select
            value={form.role}
            onChange={(e) => handleChange('role', e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            {ROLE_OPTIONS.map((role) => (
              <option key={role} value={role}>{role}</option>
            ))}
          </select>
        </div>

        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => handleChange('is_active', e.target.checked)}
          />
          Usuário ativo
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm disabled:opacity-60"
          >
            {isSubmitting ? 'Salvando...' : isEditing ? 'Salvar' : 'Criar'}
          </button>
          {isEditing && (
            <button
              type="button"
              onClick={resetForm}
              className="px-4 py-2 rounded-lg bg-gray-200 text-gray-800 text-sm"
            >
              Cancelar
            </button>
          )}
        </div>
      </form>

      <section className="bg-white border border-gray-200 rounded-xl">
        <div className="px-4 py-3 border-b border-gray-100">
          <h3 className="font-semibold text-gray-800">Usuários</h3>
        </div>

        {isLoading ? (
          <p className="p-4 text-sm text-gray-500">Carregando...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="text-left px-4 py-2">Nome</th>
                  <th className="text-left px-4 py-2">E-mail</th>
                  <th className="text-left px-4 py-2">Role</th>
                  <th className="text-left px-4 py-2">Status</th>
                  <th className="text-right px-4 py-2">Ações</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} className="border-t border-gray-100">
                    <td className="px-4 py-2">{user.name}</td>
                    <td className="px-4 py-2">{user.email}</td>
                    <td className="px-4 py-2">{user.role}</td>
                    <td className="px-4 py-2">{user.is_active ? 'Ativo' : 'Inativo'}</td>
                    <td className="px-4 py-2 text-right space-x-2">
                      <button
                        type="button"
                        onClick={() => startEdit(user)}
                        className="px-3 py-1 rounded bg-amber-100 text-amber-800"
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(user.id)}
                        className="px-3 py-1 rounded bg-red-100 text-red-700"
                      >
                        Excluir
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

export default UsersAdminPage

import { useEffect, useState } from 'react'
import api from '../api/client.js'
import useAuth from '../hooks/use_auth.js'

function ProfilePage() {
  const { user, refreshUser } = useAuth()
  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    specialty: '',
    profile_notes: '',
  })
  const [avatarFile, setAvatarFile] = useState(null)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const avatarUrl = user?.avatar_url || null

  useEffect(() => {
    if (!user) return
    setForm({
      name: user.name || '',
      email: user.email || '',
      phone: user.phone || '',
      specialty: user.specialty || '',
      profile_notes: user.profile_notes || '',
    })
  }, [user])

  const handleChange = (field) => (event) => {
    setForm((prev) => ({ ...prev, [field]: event.target.value }))
  }

  const handleSave = async (event) => {
    event.preventDefault()
    setError('')
    setStatus('')
    try {
      await api.put('/me', form)
      await refreshUser()
      setStatus('Perfil atualizado com sucesso.')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Não foi possível salvar o perfil.')
    }
  }

  const handleAvatarUpload = async () => {
    if (!avatarFile) return
    setError('')
    setStatus('')
    try {
      const data = new FormData()
      data.append('file', avatarFile)
      await api.post('/me/avatar', data, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      await refreshUser()
      setStatus('Avatar atualizado com sucesso.')
      setAvatarFile(null)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Não foi possível enviar o avatar.')
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Meu Perfil</h1>
        <p className="text-sm text-gray-500">Gerencie seus dados e imagem de perfil.</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 flex gap-6 items-center">
        <div className="w-20 h-20 rounded-full overflow-hidden bg-gray-100 border border-gray-200 flex items-center justify-center text-gray-400 text-xl">
          {avatarUrl ? <img src={avatarUrl} alt="Avatar" className="w-full h-full object-cover" /> : '👤'}
        </div>
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 mb-2">Avatar (PNG/JPG/WEBP até 2MB)</label>
          <div className="flex items-center gap-3">
            <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => setAvatarFile(e.target.files?.[0] || null)} />
            <button
              type="button"
              onClick={handleAvatarUpload}
              disabled={!avatarFile}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
            >
              Enviar avatar
            </button>
          </div>
        </div>
      </div>

      <form onSubmit={handleSave} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="text-sm text-gray-700">
            Nome
            <input className="mt-1 w-full border rounded-lg px-3 py-2" value={form.name} onChange={handleChange('name')} />
          </label>
          <label className="text-sm text-gray-700">
            E-mail
            <input className="mt-1 w-full border rounded-lg px-3 py-2" value={form.email} onChange={handleChange('email')} />
          </label>
          <label className="text-sm text-gray-700">
            Telefone
            <input className="mt-1 w-full border rounded-lg px-3 py-2" value={form.phone} onChange={handleChange('phone')} />
          </label>
          <label className="text-sm text-gray-700">
            Cargo/Especialidade
            <input className="mt-1 w-full border rounded-lg px-3 py-2" value={form.specialty} onChange={handleChange('specialty')} />
          </label>
        </div>
        <label className="text-sm text-gray-700 block">
          Observações cadastrais
          <textarea className="mt-1 w-full border rounded-lg px-3 py-2 min-h-24" value={form.profile_notes} onChange={handleChange('profile_notes')} />
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {status && <p className="text-sm text-green-700">{status}</p>}

        <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm">
          Salvar alterações
        </button>
      </form>
    </div>
  )
}

export default ProfilePage

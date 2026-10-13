import { useState, useEffect } from 'react'
import { Shield, Plus, Trash2, Pencil, Check, X, Loader2, Wifi, WifiOff, Clock, AlertTriangle } from 'lucide-react'
import { api } from '../services/api'

const PROXY_TYPES = ['DIRECT', 'HTTP', 'HTTPS', 'SOCKS5', 'BURP', 'CUSTOM']

const DEFAULT_FORM = {
  name: '',
  type: 'DIRECT',
  host: '',
  port: '',
  username: '',
  password: '',
}

function OutcomeBadge({ outcome }) {
  if (!outcome) return null
  const map = {
    Connected: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
    Failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    Timeout: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    'Authentication failed': 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  }
  const icon = {
    Connected: <Wifi className="w-3 h-3 inline mr-1" />,
    Failed: <WifiOff className="w-3 h-3 inline mr-1" />,
    Timeout: <Clock className="w-3 h-3 inline mr-1" />,
    'Authentication failed': <AlertTriangle className="w-3 h-3 inline mr-1" />,
  }
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${map[outcome] || ''}`}>
      {icon[outcome]}{outcome}
    </span>
  )
}

export default function ProxyManager() {
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(DEFAULT_FORM)
  const [saving, setSaving] = useState(false)
  const [testResults, setTestResults] = useState({})  // id -> outcome
  const [testing, setTesting] = useState({})  // id -> bool

  const load = async () => {
    try {
      const data = await api.get('/proxy-profiles')
      setProfiles(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const openCreate = () => {
    setEditingId(null)
    setForm(DEFAULT_FORM)
    setShowForm(true)
  }

  const openEdit = (p) => {
    setEditingId(p.id)
    setForm({ name: p.name, type: p.type, host: p.host || '', port: p.port || '', username: p.username || '', password: '' })
    setShowForm(true)
  }

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const body = {
        ...form,
        port: form.port ? Number(form.port) : undefined,
        password: form.password || undefined,
      }
      if (editingId) {
        await api.patch(`/proxy-profiles/${editingId}`, body)
      } else {
        await api.post('/proxy-profiles', body)
      }
      setShowForm(false)
      load()
    } catch (e) {
      alert(e.message || 'Failed to save proxy profile')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this proxy profile?')) return
    await api.delete(`/proxy-profiles/${id}`)
    load()
  }

  const handleTest = async (id) => {
    setTesting(prev => ({ ...prev, [id]: true }))
    try {
      const result = await api.post(`/proxy-profiles/${id}/test`, {})
      setTestResults(prev => ({ ...prev, [id]: result.outcome }))
    } catch {
      setTestResults(prev => ({ ...prev, [id]: 'Failed' }))
    } finally {
      setTesting(prev => ({ ...prev, [id]: false }))
    }
  }

  const needsHost = form.type !== 'DIRECT'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-6 h-6 text-blue-500" />
          <h1 className="text-2xl font-bold dark:text-white">Proxy Manager</h1>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          New Profile
        </button>
      </div>

      {/* Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <form
            onSubmit={handleSave}
            className="bg-white dark:bg-slate-800 rounded-xl shadow-xl p-6 w-full max-w-md space-y-4"
          >
            <h2 className="text-lg font-semibold dark:text-white">
              {editingId ? 'Edit Proxy Profile' : 'New Proxy Profile'}
            </h2>

            <div>
              <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Name</label>
              <input
                required
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="mt-1 w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-white"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Type</label>
              <select
                value={form.type}
                onChange={e => setForm(f => ({ ...f, type: e.target.value }))}
                className="mt-1 w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-white"
              >
                {PROXY_TYPES.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>

            {needsHost && (
              <>
                <div className="flex gap-3">
                  <div className="flex-1">
                    <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Host</label>
                    <input
                      required
                      value={form.host}
                      onChange={e => setForm(f => ({ ...f, host: e.target.value }))}
                      placeholder="127.0.0.1"
                      className="mt-1 w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-white"
                    />
                  </div>
                  <div className="w-28">
                    <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Port</label>
                    <input
                      required
                      type="number"
                      min={1} max={65535}
                      value={form.port}
                      onChange={e => setForm(f => ({ ...f, port: e.target.value }))}
                      placeholder="8080"
                      className="mt-1 w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-white"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Username (optional)</label>
                  <input
                    value={form.username}
                    onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                    className="mt-1 w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-white"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium text-slate-600 dark:text-slate-400">
                    Password {editingId ? '(leave blank to keep existing)' : '(optional)'}
                  </label>
                  <input
                    type="password"
                    value={form.password}
                    onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                    className="mt-1 w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-white"
                  />
                </div>
              </>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
              >
                {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                {editingId ? 'Update' : 'Create'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-blue-500" /></div>
      ) : profiles.length === 0 ? (
        <div className="text-center py-16 text-slate-500 dark:text-slate-400">
          <Shield className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>No proxy profiles yet. Create one to route scans through a proxy.</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-900 text-slate-500 dark:text-slate-400">
              <tr>
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">Type</th>
                <th className="px-4 py-3 text-left">Host:Port</th>
                <th className="px-4 py-3 text-left">Auth</th>
                <th className="px-4 py-3 text-left">Last Test</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {profiles.map(p => (
                <tr key={p.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50">
                  <td className="px-4 py-3 font-medium dark:text-white">{p.name}</td>
                  <td className="px-4 py-3">
                    <span className="bg-slate-100 dark:bg-slate-700 dark:text-slate-200 text-slate-700 text-xs px-2 py-0.5 rounded font-mono">
                      {p.type}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-500 dark:text-slate-400">
                    {p.host ? `${p.host}:${p.port}` : '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                    {p.username ? (
                      <span className="flex items-center gap-1">
                        <Check className="w-3 h-3 text-emerald-500" />
                        {p.username}{p.has_secret ? ' + pwd' : ''}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <OutcomeBadge outcome={testResults[p.id]} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleTest(p.id)}
                        disabled={testing[p.id]}
                        className="text-xs px-2 py-1 bg-slate-100 dark:bg-slate-700 dark:text-slate-300 rounded hover:bg-slate-200 dark:hover:bg-slate-600 flex items-center gap-1"
                        title="Test connectivity"
                      >
                        {testing[p.id] ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wifi className="w-3 h-3" />}
                        Test
                      </button>
                      <button onClick={() => openEdit(p)} className="text-slate-400 hover:text-blue-500">
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button onClick={() => handleDelete(p.id)} className="text-slate-400 hover:text-red-500">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

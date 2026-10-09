import { useState, useEffect } from 'react'
import { api } from '../services/api'

export default function Projects() {
  const [projects, setProjects] = useState([])
  const [error, setError] = useState(null)
  
  const [newName, setNewName] = useState('')
  const [authorizedAck, setAuthorizedAck] = useState(false)
  
  const [newTargetValues, setNewTargetValues] = useState({})

  const fetchProjects = () => {
    api.get('/api/projects')
      .then(async data => {
        const fullData = await Promise.all(data.map(async p => {
          try {
            const targets = await api.get(`/api/projects/${p.id}/targets`)
            return { ...p, targets }
          } catch (e) {
            return { ...p, targets: [] }
          }
        }))
        setProjects(fullData)
      })
      .catch(err => setError(err.message))
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  const handleCreateProject = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      await api.post('/api/projects', { name: newName, authorized_ack: authorizedAck })
      setNewName('')
      setAuthorizedAck(false)
      fetchProjects()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleAddTarget = async (projectId) => {
    setError(null)
    const val = newTargetValues[projectId]
    if (!val) return
    try {
      await api.post(`/api/projects/${projectId}/targets`, { value: val })
      setNewTargetValues({ ...newTargetValues, [projectId]: '' })
      fetchProjects()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Projects</h2>
      
      {error && (
        <div className="p-4 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-md border border-red-200 dark:border-red-800">
          {error}
        </div>
      )}

      <div className="bg-white dark:bg-slate-900 p-6 rounded-lg shadow-sm border border-slate-200 dark:border-slate-800">
        <h3 className="text-lg font-semibold mb-4 text-slate-800 dark:text-slate-100">Create New Project</h3>
        <form onSubmit={handleCreateProject} className="space-y-4 max-w-md">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Project Name</label>
            <input 
              type="text" 
              required
              value={newName}
              onChange={e => setNewName(e.target.value)}
              className="w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-900 dark:text-slate-100"
            />
          </div>
          <div className="flex items-center gap-2">
            <input 
              type="checkbox" 
              id="ack"
              checked={authorizedAck}
              onChange={e => setAuthorizedAck(e.target.checked)}
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="ack" className="text-sm text-slate-700 dark:text-slate-300">
              I am authorized to test these targets
            </label>
          </div>
          <button 
            type="submit" 
            disabled={!authorizedAck || !newName}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Create Project
          </button>
        </form>
      </div>

      <div className="space-y-4">
        {projects.map(p => (
          <div key={p.id} className="bg-white dark:bg-slate-900 p-6 rounded-lg shadow-sm border border-slate-200 dark:border-slate-800">
            <h3 className="text-xl font-semibold mb-2 text-slate-800 dark:text-slate-100">{p.name}</h3>
            
            <div className="mb-4">
              <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Targets</h4>
              {p.targets && p.targets.length > 0 ? (
                <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-400">
                  {p.targets.map(t => <li key={t.id}>{t.value}</li>)}
                </ul>
              ) : (
                <p className="text-sm text-slate-500">No targets added yet.</p>
              )}
            </div>

            <div className="flex items-center gap-2 max-w-md">
              <input 
                type="text"
                placeholder="Add a target (e.g. example.com)"
                value={newTargetValues[p.id] || ''}
                onChange={e => setNewTargetValues({ ...newTargetValues, [p.id]: e.target.value })}
                className="flex-1 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-900 dark:text-slate-100"
              />
              <button 
                onClick={() => handleAddTarget(p.id)}
                disabled={!newTargetValues[p.id]}
                className="px-4 py-2 bg-slate-800 dark:bg-slate-700 text-white rounded-md text-sm font-medium hover:bg-slate-700 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Add Target
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

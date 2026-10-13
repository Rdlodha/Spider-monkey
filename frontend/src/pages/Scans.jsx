import { useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'

const SUPPORTED_TOOLS = [
  { value: 'nmap', label: 'Nmap (XML)' },
  { value: 'feroxbuster', label: 'Feroxbuster (JSON lines)' },
  { value: 'gobuster', label: 'Gobuster (text)' },
]

function StatusBadge({ status }) {
  const colors = {
    completed: 'bg-green-700 text-green-100',
    running: 'bg-blue-700 text-blue-100',
    failed: 'bg-red-700 text-red-100',
    queued: 'bg-yellow-700 text-yellow-100',
    cancelled: 'bg-slate-600 text-slate-200',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${colors[status] || 'bg-slate-600 text-slate-200'}`}>
      {status}
    </span>
  )
}

function ImportForm({ projects, onImported }) {
  const [projectId, setProjectId] = useState('')
  const [tool, setTool] = useState('nmap')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!projectId || !file) {
      setError('Please select a project and a file.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const fd = new FormData()
      fd.append('project_id', projectId)
      fd.append('tool', tool)
      fd.append('file', file)
      await api.upload('/api/scans/import', fd)
      setFile(null)
      e.target.reset()
      onImported()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-slate-800 rounded-lg p-5 space-y-4">
      <h2 className="text-lg font-semibold text-white">Import Scan Output</h2>

      {error && (
        <div className="bg-red-900/60 border border-red-500 text-red-200 text-sm px-3 py-2 rounded">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="project-select" className="block text-sm text-slate-400 mb-1">Project</label>
          <select
            id="project-select"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            required
            className="w-full bg-slate-700 text-white border border-slate-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">— Select project —</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="tool-select" className="block text-sm text-slate-400 mb-1">Tool</label>
          <select
            id="tool-select"
            value={tool}
            onChange={(e) => setTool(e.target.value)}
            className="w-full bg-slate-700 text-white border border-slate-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {SUPPORTED_TOOLS.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label htmlFor="file-input" className="block text-sm text-slate-400 mb-1">Output file</label>
        <input
          id="file-input"
          type="file"
          required
          onChange={(e) => setFile(e.target.files[0] || null)}
          className="w-full text-sm text-slate-300 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-blue-600 file:text-white file:cursor-pointer hover:file:bg-blue-500"
        />
        <p className="text-xs text-slate-500 mt-1">Max 50 MB. Nmap → XML. Feroxbuster → JSON lines. Gobuster → text.</p>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium px-4 py-2 rounded text-sm transition-colors"
      >
        {loading ? 'Importing…' : 'Import'}
      </button>
    </form>
  )
}

function ScanDetail({ scan, onClose }) {
  const [detail, setDetail] = useState(null)
  const [hostDetail, setHostDetail] = useState(null)
  const [loadingHost, setLoadingHost] = useState(false)

  useEffect(() => {
    api.get(`/api/scans/${scan.id}`).then(setDetail).catch(console.error)
  }, [scan.id])

  async function loadHostDetail(hostId) {
    setLoadingHost(true)
    try {
      const h = await api.get(`/api/hosts/${hostId}`)
      setHostDetail(h)
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingHost(false)
    }
  }

  if (!detail) {
    return (
      <div className="bg-slate-800 rounded-lg p-5 text-slate-400 text-sm">
        Loading scan details…
      </div>
    )
  }

  // Parse error list if stored as JSON
  let parseErrors = []
  if (detail.error) {
    try { parseErrors = JSON.parse(detail.error) } catch { parseErrors = [detail.error] }
  }

  return (
    <div className="bg-slate-800 rounded-lg p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Scan Detail</h2>
        <button onClick={onClose} className="text-slate-400 hover:text-white text-sm">✕ Close</button>
      </div>

      <div className="grid grid-cols-3 gap-3 text-sm">
        <div>
          <span className="text-slate-400">Tool</span>
          <p className="text-white font-medium">{detail.tool}</p>
        </div>
        <div>
          <span className="text-slate-400">Status</span>
          <p><StatusBadge status={detail.status} /></p>
        </div>
        <div>
          <span className="text-slate-400">SHA-256</span>
          <p className="text-white font-mono text-xs truncate">{detail.raw_sha256 || '—'}</p>
        </div>
        <div>
          <span className="text-slate-400">Started</span>
          <p className="text-white">{detail.started_at ? new Date(detail.started_at).toLocaleString() : '—'}</p>
        </div>
        <div>
          <span className="text-slate-400">Completed</span>
          <p className="text-white">{detail.completed_at ? new Date(detail.completed_at).toLocaleString() : '—'}</p>
        </div>
      </div>

      {parseErrors.length > 0 && (
        <div className="bg-yellow-900/40 border border-yellow-600 rounded p-3">
          <p className="text-yellow-300 text-sm font-semibold mb-1">Parse Warnings ({parseErrors.length})</p>
          <ul className="text-yellow-200 text-xs space-y-0.5">
            {parseErrors.map((e, i) => <li key={i}>• {e}</li>)}
          </ul>
        </div>
      )}

      {/* Hosts */}
      {detail.hosts.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-300 mb-2">
            Hosts ({detail.hosts.length})
          </h3>
          <div className="space-y-1">
            {detail.hosts.map((h) => (
              <div
                key={h.id}
                className="flex items-center justify-between bg-slate-700 hover:bg-slate-600 rounded px-3 py-2 text-sm transition-colors"
              >
                <button
                  onClick={() => loadHostDetail(h.id)}
                  className="flex-1 text-left flex items-center gap-2"
                >
                  <span className="text-white font-mono">{h.ip}</span>
                  {h.hostname && <span className="text-slate-400">({h.hostname})</span>}
                </button>
                <button
                  onClick={async (e) => {
                    e.stopPropagation()
                    try {
                      const updated = await api.patch(`/api/hosts/${h.id}/interesting`)
                      setDetail((prev) => ({
                        ...prev,
                        hosts: prev.hosts.map((host) => (host.id === h.id ? { ...host, is_interesting: updated.is_interesting } : host)),
                      }))
                    } catch (err) {
                      console.error(err)
                    }
                  }}
                  title="Toggle interesting"
                  className={`text-xs px-2 py-0.5 rounded border transition-colors ${
                    h.is_interesting ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'text-slate-400 border-slate-600 hover:text-white'
                  }`}
                >
                  ★ {h.is_interesting ? 'Flagged' : 'Flag'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Host detail panel */}
      {loadingHost && <p className="text-slate-400 text-sm">Loading host…</p>}
      {hostDetail && !loadingHost && (
        <div className="bg-slate-700 rounded p-3 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-white font-semibold font-mono">{hostDetail.ip}</p>
            <button onClick={() => setHostDetail(null)} className="text-slate-400 hover:text-white text-xs">✕</button>
          </div>
          {hostDetail.hostname && <p className="text-slate-400 text-xs">{hostDetail.hostname}</p>}
          {hostDetail.services.length === 0 ? (
            <p className="text-slate-500 text-xs">No services recorded.</p>
          ) : (
            <table className="w-full text-xs text-slate-200">
              <thead>
                <tr className="text-slate-400 border-b border-slate-600">
                  <th className="text-left py-1">Port</th>
                  <th className="text-left py-1">Proto</th>
                  <th className="text-left py-1">State</th>
                  <th className="text-left py-1">Service</th>
                  <th className="text-left py-1">Product / Version</th>
                  <th className="text-right py-1">Actions</th>
                </tr>
              </thead>
              <tbody>
                {hostDetail.services.map((s) => (
                  <tr key={s.id} className="border-b border-slate-700/50">
                    <td className="py-1 font-mono font-bold">{s.port}</td>
                    <td className="py-1">{s.protocol}</td>
                    <td className="py-1">
                      <span className={s.state === 'open' ? 'text-green-400' : 'text-slate-400'}>{s.state}</span>
                    </td>
                    <td className="py-1">{s.name || '—'}</td>
                    <td className="py-1 text-slate-400">{[s.product, s.version].filter(Boolean).join(' ') || '—'}</td>
                    <td className="py-1 text-right space-x-1.5 whitespace-nowrap">
                      <button
                        onClick={async () => {
                          try {
                            const updated = await api.patch(`/api/hosts/services/${s.id}/interesting`)
                            setHostDetail((prev) => ({
                              ...prev,
                              services: prev.services.map((svc) => (svc.id === s.id ? updated : svc)),
                            }))
                          } catch (err) {
                            console.error(err)
                          }
                        }}
                        className={`text-[10px] px-1.5 py-0.5 rounded border ${
                          s.is_interesting ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'text-slate-400 border-slate-600'
                        }`}
                      >
                        ★
                      </button>
                      <button
                        onClick={async () => {
                          try {
                            await api.post('/api/findings', {
                              project_id: detail.project_id,
                              title: `Service ${hostDetail.ip}:${s.port}/${s.protocol} (${s.name || 'unknown'})`,
                              description: `Discovered running service: ${[s.product, s.version].filter(Boolean).join(' ') || s.name || s.protocol}`,
                              severity: 'INFO',
                              source_tool: detail.tool,
                              source_scan_id: detail.id,
                              links: [{ entity_type: 'service', entity_id: s.id }],
                            })
                            alert('Finding created from service!')
                          } catch (err) {
                            alert(err.message)
                          }
                        }}
                        className="text-[10px] bg-blue-600 hover:bg-blue-500 text-white px-2 py-0.5 rounded"
                      >
                        + Finding
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Endpoints */}
      {detail.endpoints.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-300 mb-2">
            Endpoints ({detail.endpoints.length})
          </h3>
          <table className="w-full text-xs text-slate-200">
            <thead>
              <tr className="text-slate-400 border-b border-slate-600">
                <th className="text-left py-1">Status</th>
                <th className="text-left py-1">URL</th>
                <th className="text-left py-1">Size</th>
                <th className="text-left py-1">Tool</th>
                <th className="text-right py-1">Actions</th>
              </tr>
            </thead>
            <tbody>
              {detail.endpoints.map((ep) => (
                <tr key={ep.id} className="border-b border-slate-700/50">
                  <td className="py-1 font-bold" style={{ color: ep.status_code >= 200 && ep.status_code < 300 ? '#4ade80' : ep.status_code >= 300 && ep.status_code < 400 ? '#facc15' : '#f87171' }}>
                    {ep.status_code ?? '—'}
                  </td>
                  <td className="py-1 font-mono truncate max-w-xs">{ep.url}</td>
                  <td className="py-1 text-slate-400">{ep.content_length ?? '—'}</td>
                  <td className="py-1 text-slate-400">{ep.source_tool}</td>
                  <td className="py-1 text-right space-x-1.5 whitespace-nowrap">
                    <button
                      onClick={async () => {
                        try {
                          const updated = await api.patch(`/api/endpoints/${ep.id}/interesting`)
                          setDetail((prev) => ({
                            ...prev,
                            endpoints: prev.endpoints.map((e) => (e.id === ep.id ? updated : e)),
                          }))
                        } catch (err) {
                          console.error(err)
                        }
                      }}
                      className={`text-[10px] px-1.5 py-0.5 rounded border ${
                        ep.is_interesting ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'text-slate-400 border-slate-600'
                      }`}
                    >
                      ★
                    </button>
                    <button
                      onClick={async () => {
                        try {
                          await api.post('/api/findings', {
                            project_id: detail.project_id,
                            title: `Discovered endpoint: ${ep.path || ep.url}`,
                            description: `Endpoint returned HTTP ${ep.status_code ?? 'unknown'} with length ${ep.content_length ?? 'unknown'} bytes. Source tool: ${ep.source_tool}`,
                            severity: 'INFO',
                            source_tool: ep.source_tool,
                            source_scan_id: detail.id,
                            links: [{ entity_type: 'endpoint', entity_id: ep.id }],
                          })
                          alert('Finding created from endpoint!')
                        } catch (err) {
                          alert(err.message)
                        }
                      }}
                      className="text-[10px] bg-blue-600 hover:bg-blue-500 text-white px-2 py-0.5 rounded"
                    >
                      + Finding
                    </button>
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

export default function Scans() {
  const [projects, setProjects] = useState([])
  const [scans, setScans] = useState([])
  const [selectedScan, setSelectedScan] = useState(null)
  const [filterProject, setFilterProject] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchScans = useCallback(async () => {
    setLoading(true)
    try {
      const url = filterProject ? `/api/scans?project_id=${filterProject}` : '/api/scans'
      const [s] = await Promise.all([api.get(url)])
      setScans(s)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [filterProject])

  useEffect(() => {
    api.get('/api/projects').then(setProjects).catch(console.error)
  }, [])

  useEffect(() => {
    fetchScans()
  }, [fetchScans])

  return (
    <div className="p-6 space-y-6 text-slate-100">
      <h1 className="text-2xl font-bold">Scans</h1>

      <ImportForm projects={projects} onImported={fetchScans} />

      {/* Scan history */}
      <div className="bg-slate-800 rounded-lg p-5 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h2 className="text-lg font-semibold text-white">Scan History</h2>
          <div className="flex items-center gap-2">
            <select
              value={filterProject}
              onChange={(e) => setFilterProject(e.target.value)}
              className="bg-slate-700 text-white border border-slate-600 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All projects</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <button
              onClick={fetchScans}
              className="bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded text-sm transition-colors"
            >
              ↺ Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="text-red-400 text-sm">{error}</div>
        )}

        {loading ? (
          <p className="text-slate-400 text-sm">Loading…</p>
        ) : scans.length === 0 ? (
          <p className="text-slate-500 text-sm">No scans yet. Import a tool output file above.</p>
        ) : (
          <table className="w-full text-sm text-slate-200">
            <thead>
              <tr className="text-slate-400 border-b border-slate-600">
                <th className="text-left py-2">Tool</th>
                <th className="text-left py-2">Status</th>
                <th className="text-left py-2">SHA-256</th>
                <th className="text-left py-2">Created</th>
                <th className="text-left py-2"></th>
              </tr>
            </thead>
            <tbody>
              {scans.map((scan) => (
                <tr key={scan.id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                  <td className="py-2 font-medium">{scan.tool}</td>
                  <td className="py-2"><StatusBadge status={scan.status} /></td>
                  <td className="py-2 font-mono text-xs text-slate-400 truncate max-w-[120px]">{scan.raw_sha256?.slice(0, 12)}…</td>
                  <td className="py-2 text-slate-400 text-xs">{new Date(scan.created_at).toLocaleString()}</td>
                  <td className="py-2">
                    <button
                      onClick={() => setSelectedScan(scan)}
                      className="text-blue-400 hover:text-blue-300 text-xs"
                    >
                      Details →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Scan detail panel */}
      {selectedScan && (
        <ScanDetail
          scan={selectedScan}
          onClose={() => setSelectedScan(null)}
        />
      )}
    </div>
  )
}

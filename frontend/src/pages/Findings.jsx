import { useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'
import {
  AlertCircle,
  Plus,
  Trash2,
  ExternalLink,
  Upload,
  FileText,
  Download,
  CheckCircle,
  XCircle,
  Tag,
  Paperclip,
  Sparkles,
  Link as LinkIcon
} from 'lucide-react'

const SEVERITIES = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']
const STATUSES = ['OPEN', 'INVESTIGATING', 'CONFIRMED', 'FALSE_POSITIVE', 'RESOLVED']

const SEVERITY_COLORS = {
  CRITICAL: 'bg-red-500/20 text-red-400 border-red-500/30',
  HIGH: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  LOW: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  INFO: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
}

const STATUS_COLORS = {
  OPEN: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  INVESTIGATING: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  CONFIRMED: 'bg-red-500/10 text-red-400 border-red-500/20',
  FALSE_POSITIVE: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
  RESOLVED: 'bg-green-500/10 text-green-400 border-green-500/20',
}

export default function Findings() {
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState('')
  const [findings, setFindings] = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [dismissedSuggestions, setDismissedSuggestions] = useState(new Set())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Filters
  const [filterSeverity, setFilterSeverity] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterTag, setFilterTag] = useState('')

  // Modals & Active Finding
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedFinding, setSelectedFinding] = useState(null)

  // Form State
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    severity: 'INFO',
    status: 'OPEN',
    notes: '',
    tags: '',
    source_tool: 'manual',
    links: [],
  })

  // Evidence Form State
  const [evidenceFile, setEvidenceFile] = useState(null)
  const [evidenceText, setEvidenceText] = useState('')
  const [evidenceError, setEvidenceError] = useState(null)

  // Link Form State
  const [newLinkType, setNewLinkType] = useState('host')
  const [newLinkId, setNewLinkId] = useState('')

  // Load Projects
  useEffect(() => {
    api.get('/api/projects')
      .then((data) => {
        setProjects(data)
        if (data.length > 0) {
          setSelectedProject(data[0].id)
        }
      })
      .catch((err) => setError(err.message))
  }, [])

  // Fetch Findings and Suggestions
  const fetchFindings = useCallback(async () => {
    if (!selectedProject) return
    setLoading(true)
    setError(null)
    try {
      let url = `/api/findings?project_id=${selectedProject}`
      if (filterSeverity) url += `&severity=${filterSeverity}`
      if (filterStatus) url += `&status=${filterStatus}`
      if (filterTag) url += `&tag=${encodeURIComponent(filterTag)}`

      const [findingsData, corrData] = await Promise.all([
        api.get(url),
        api.get(`/api/correlate/${selectedProject}`).catch(() => ({ suggestions: [] })),
      ])
      setFindings(findingsData)
      setSuggestions(corrData.suggestions || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [selectedProject, filterSeverity, filterStatus, filterTag])

  useEffect(() => {
    fetchFindings()
  }, [fetchFindings])

  // Select / Refresh single finding detail
  const refreshFindingDetail = async (findingId) => {
    try {
      const detail = await api.get(`/api/findings/${findingId}`)
      setSelectedFinding(detail)
      setFindings((prev) => prev.map((f) => (f.id === detail.id ? detail : f)))
    } catch (err) {
      setError(err.message)
    }
  }

  // Handle Create or Update Finding
  const handleSubmitFinding = async (e) => {
    e.preventDefault()
    try {
      if (formData.id) {
        await api.patch(`/api/findings/${formData.id}`, formData)
      } else {
        await api.post('/api/findings', { ...formData, project_id: selectedProject })
      }
      setShowCreateModal(false)
      setFormData({
        title: '',
        description: '',
        severity: 'INFO',
        status: 'OPEN',
        notes: '',
        tags: '',
        source_tool: 'manual',
        links: [],
      })
      fetchFindings()
    } catch (err) {
      setError(err.message)
    }
  }

  // Handle Delete Finding
  const handleDeleteFinding = async (id) => {
    if (!window.confirm('Are you sure you want to delete this finding?')) return
    try {
      await api.delete(`/api/findings/${id}`)
      if (selectedFinding?.id === id) setSelectedFinding(null)
      fetchFindings()
    } catch (err) {
      setError(err.message)
    }
  }

  // Accept Correlation Suggestion
  const handleAcceptSuggestion = (s) => {
    setFormData({
      title: s.title,
      description: s.description,
      severity: s.severity,
      status: 'OPEN',
      notes: `Suggested by rule ${s.rule_id} for ${s.entity_label}`,
      tags: 'correlated',
      source_tool: 'correlation',
      links: [{ entity_type: s.entity_type, entity_id: s.entity_id }],
    })
    setShowCreateModal(true)
  }

  const handleDismissSuggestion = (ruleId, entityId) => {
    setDismissedSuggestions((prev) => new Set(prev).add(`${ruleId}:${entityId}`))
  }

  // Evidence Upload
  const handleUploadEvidence = async (e) => {
    e.preventDefault()
    if (!evidenceFile || !selectedFinding) return
    setEvidenceError(null)
    const data = new FormData()
    data.append('file', evidenceFile)
    try {
      await api.upload(`/api/findings/${selectedFinding.id}/evidence/file`, data)
      setEvidenceFile(null)
      refreshFindingDetail(selectedFinding.id)
    } catch (err) {
      setEvidenceError(err.message)
    }
  }

  // Evidence Paste
  const handlePasteEvidence = async (e) => {
    e.preventDefault()
    if (!evidenceText.trim() || !selectedFinding) return
    setEvidenceError(null)
    const data = new FormData()
    data.append('text', evidenceText)
    try {
      await api.upload(`/api/findings/${selectedFinding.id}/evidence/text`, data)
      setEvidenceText('')
      refreshFindingDetail(selectedFinding.id)
    } catch (err) {
      setEvidenceError(err.message)
    }
  }

  // Evidence Delete
  const handleDeleteEvidence = async (evidenceId) => {
    if (!window.confirm('Delete this evidence?')) return
    try {
      await api.delete(`/api/findings/${selectedFinding.id}/evidence/${evidenceId}`)
      refreshFindingDetail(selectedFinding.id)
    } catch (err) {
      setError(err.message)
    }
  }

  // Add Link
  const handleAddLink = async (e) => {
    e.preventDefault()
    if (!newLinkId.trim() || !selectedFinding) return
    try {
      await api.post(`/api/findings/${selectedFinding.id}/links`, {
        entity_type: newLinkType,
        entity_id: newLinkId.trim(),
      })
      setNewLinkId('')
      refreshFindingDetail(selectedFinding.id)
    } catch (err) {
      setError(err.message)
    }
  }

  // Remove Link
  const handleRemoveLink = async (linkId) => {
    try {
      await api.delete(`/api/findings/${selectedFinding.id}/links/${linkId}`)
      refreshFindingDetail(selectedFinding.id)
    } catch (err) {
      setError(err.message)
    }
  }

  const visibleSuggestions = suggestions.filter(
    (s) => !dismissedSuggestions.has(`${s.rule_id}:${s.entity_id}`)
  )

  return (
    <div className="p-6 space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <AlertCircle className="w-6 h-6 text-blue-400" /> Findings & Evidence
          </h1>
          <p className="text-sm text-slate-400">
            Track vulnerabilities, correlated discoveries, and verified evidence
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="bg-slate-800 text-white border border-slate-700 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>

          <button
            onClick={() => {
              setFormData({
                title: '',
                description: '',
                severity: 'INFO',
                status: 'OPEN',
                notes: '',
                tags: '',
                source_tool: 'manual',
                links: [],
              })
              setShowCreateModal(true)
            }}
            className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded text-sm flex items-center gap-1.5 font-medium transition-colors"
          >
            <Plus className="w-4 h-4" /> New Finding
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/50 border border-red-500 text-red-200 text-sm px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Correlation Suggestions Banner */}
      {visibleSuggestions.length > 0 && (
        <div className="bg-slate-800/90 border border-blue-500/30 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-blue-400 flex items-center gap-2">
              <Sparkles className="w-4 h-4" /> Suggested Correlations ({visibleSuggestions.length})
            </h3>
            <span className="text-xs text-slate-400">
              Deterministic rule detections from your imported scans
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {visibleSuggestions.map((s) => (
              <div
                key={`${s.rule_id}:${s.entity_id}`}
                className="bg-slate-900/80 border border-slate-700/60 rounded p-3 text-xs flex flex-col justify-between space-y-2"
              >
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className={`px-1.5 py-0.5 rounded font-bold border ${SEVERITY_COLORS[s.severity]}`}>
                      {s.severity}
                    </span>
                    <span className="text-slate-500 font-mono text-[10px]">{s.rule_id}</span>
                  </div>
                  <h4 className="font-semibold text-slate-200">{s.title}</h4>
                  <p className="text-slate-400 line-clamp-2 mt-1">{s.description}</p>
                  <p className="text-slate-500 font-mono mt-1 truncate">Target: {s.entity_label}</p>
                </div>
                <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
                  <button
                    onClick={() => handleAcceptSuggestion(s)}
                    className="flex-1 bg-blue-600/80 hover:bg-blue-600 text-white py-1 rounded text-center transition-colors font-medium"
                  >
                    Accept (Create Finding)
                  </button>
                  <button
                    onClick={() => handleDismissSuggestion(s.rule_id, s.entity_id)}
                    className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 rounded transition-colors"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters Bar */}
      <div className="bg-slate-800 rounded-lg p-3 flex flex-wrap items-center gap-3 text-sm">
        <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider">Filters:</span>
        <select
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
          className="bg-slate-700 text-white rounded px-2.5 py-1 text-xs border border-slate-600 focus:outline-none"
        >
          <option value="">All Severities</option>
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="bg-slate-700 text-white rounded px-2.5 py-1 text-xs border border-slate-600 focus:outline-none"
        >
          <option value="">All Statuses</option>
          {STATUSES.map((st) => (
            <option key={st} value={st}>
              {st}
            </option>
          ))}
        </select>

        <input
          type="text"
          placeholder="Filter by tag..."
          value={filterTag}
          onChange={(e) => setFilterTag(e.target.value)}
          className="bg-slate-700 text-white rounded px-2.5 py-1 text-xs border border-slate-600 focus:outline-none w-36"
        />

        {(filterSeverity || filterStatus || filterTag) && (
          <button
            onClick={() => {
              setFilterSeverity('')
              setFilterStatus('')
              setFilterTag('')
            }}
            className="text-xs text-blue-400 hover:underline ml-auto"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Findings Table & Detail Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Findings List */}
        <div className={`space-y-3 ${selectedFinding ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
          <div className="bg-slate-800 rounded-lg overflow-hidden border border-slate-700/50">
            {loading ? (
              <p className="p-6 text-slate-400 text-sm text-center">Loading findings...</p>
            ) : findings.length === 0 ? (
              <p className="p-6 text-slate-500 text-sm text-center">
                No findings match the criteria. Create one or accept a correlation suggestion.
              </p>
            ) : (
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-900/80 text-xs text-slate-400 uppercase tracking-wider border-b border-slate-700">
                  <tr>
                    <th className="px-4 py-3">Severity</th>
                    <th className="px-4 py-3">Title</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Tags</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/40">
                  {findings.map((f) => (
                    <tr
                      key={f.id}
                      onClick={() => refreshFindingDetail(f.id)}
                      className={`hover:bg-slate-700/40 cursor-pointer transition-colors ${
                        selectedFinding?.id === f.id ? 'bg-slate-700/60' : ''
                      }`}
                    >
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span
                          className={`text-xs px-2 py-0.5 rounded font-semibold border ${
                            SEVERITY_COLORS[f.severity] || 'bg-slate-600'
                          }`}
                        >
                          {f.severity}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-medium text-white truncate max-w-xs">{f.title}</td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span
                          className={`text-xs px-2 py-0.5 rounded font-semibold border ${
                            STATUS_COLORS[f.status] || 'bg-slate-600'
                          }`}
                        >
                          {f.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-400 truncate max-w-xs">
                        {f.tags ? f.tags.split(',').map((t) => (
                          <span key={t} className="bg-slate-700/80 px-1.5 py-0.5 rounded mr-1">
                            {t.trim()}
                          </span>
                        )) : '—'}
                      </td>
                      <td className="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setFormData(f)
                            setShowCreateModal(true)
                          }}
                          className="text-xs text-blue-400 hover:text-blue-300"
                        >
                          Edit
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDeleteFinding(f.id)
                          }}
                          className="text-xs text-red-400 hover:text-red-300"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Selected Finding Detail Panel */}
        {selectedFinding && (
          <div className="bg-slate-800 rounded-lg p-5 border border-slate-700 space-y-5 text-sm h-fit">
            <div className="flex items-start justify-between">
              <div>
                <span
                  className={`text-xs px-2 py-0.5 rounded font-semibold border ${
                    SEVERITY_COLORS[selectedFinding.severity]
                  }`}
                >
                  {selectedFinding.severity}
                </span>
                <span
                  className={`ml-2 text-xs px-2 py-0.5 rounded font-semibold border ${
                    STATUS_COLORS[selectedFinding.status]
                  }`}
                >
                  {selectedFinding.status}
                </span>
                <h3 className="text-lg font-bold text-white mt-2">{selectedFinding.title}</h3>
              </div>
              <button
                onClick={() => setSelectedFinding(null)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {selectedFinding.description && (
              <div>
                <h4 className="text-xs font-semibold text-slate-400 uppercase">Description</h4>
                <p className="text-slate-300 mt-1 whitespace-pre-wrap">{selectedFinding.description}</p>
              </div>
            )}

            {selectedFinding.notes && (
              <div>
                <h4 className="text-xs font-semibold text-slate-400 uppercase">Notes</h4>
                <p className="text-slate-300 mt-1 whitespace-pre-wrap">{selectedFinding.notes}</p>
              </div>
            )}

            {/* Entity Links */}
            <div>
              <h4 className="text-xs font-semibold text-slate-400 uppercase flex items-center gap-1.5 mb-2">
                <LinkIcon className="w-3.5 h-3.5" /> Linked Entities ({selectedFinding.links?.length || 0})
              </h4>
              <div className="space-y-1.5 mb-3">
                {selectedFinding.links?.map((l) => (
                  <div
                    key={l.id}
                    className="flex items-center justify-between bg-slate-900/60 px-2.5 py-1.5 rounded text-xs"
                  >
                    <span className="font-mono text-blue-300">
                      [{l.entity_type}] {l.entity_id}
                    </span>
                    <button
                      onClick={() => handleRemoveLink(l.id)}
                      className="text-red-400 hover:text-red-300 text-xs"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>

              {/* Add Link Form */}
              <form onSubmit={handleAddLink} className="flex gap-2">
                <select
                  value={newLinkType}
                  onChange={(e) => setNewLinkType(e.target.value)}
                  className="bg-slate-700 text-white rounded px-2 py-1 text-xs border border-slate-600"
                >
                  <option value="host">Host</option>
                  <option value="service">Service</option>
                  <option value="endpoint">Endpoint</option>
                </select>
                <input
                  type="text"
                  placeholder="Entity ID..."
                  value={newLinkId}
                  onChange={(e) => setNewLinkId(e.target.value)}
                  className="flex-1 bg-slate-700 text-white rounded px-2 py-1 text-xs border border-slate-600 font-mono"
                />
                <button
                  type="submit"
                  className="bg-blue-600 hover:bg-blue-500 text-white px-2.5 py-1 rounded text-xs"
                >
                  Link
                </button>
              </form>
            </div>

            {/* Evidence Section */}
            <div className="border-t border-slate-700/60 pt-4 space-y-3">
              <h4 className="text-xs font-semibold text-slate-400 uppercase flex items-center gap-1.5">
                <Paperclip className="w-3.5 h-3.5" /> Evidence ({selectedFinding.evidence?.length || 0})
              </h4>

              {evidenceError && (
                <div className="text-red-400 text-xs bg-red-900/30 p-2 rounded">{evidenceError}</div>
              )}

              {/* Existing Evidence List */}
              <div className="space-y-2">
                {selectedFinding.evidence?.map((ev) => (
                  <div
                    key={ev.id}
                    className="bg-slate-900/70 border border-slate-700/40 rounded p-2.5 text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-200 capitalize">
                        {ev.kind}: {ev.original_filename || 'Text Note'}
                      </span>
                      <div className="flex items-center gap-2">
                        {ev.path && (
                          <button
                            onClick={() =>
                              api.download(
                                `/api/findings/${selectedFinding.id}/evidence/${ev.id}/download`,
                                ev.original_filename
                              )
                            }
                            className="text-blue-400 hover:underline flex items-center gap-1"
                          >
                            <Download className="w-3 h-3" /> Get
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteEvidence(ev.id)}
                          className="text-red-400 hover:text-red-300"
                        >
                          ✕
                        </button>
                      </div>
                    </div>

                    {ev.text && (
                      <pre className="bg-slate-950 p-2 rounded text-[11px] font-mono text-slate-300 overflow-x-auto max-h-32">
                        {ev.text}
                      </pre>
                    )}

                    {ev.sha256 && (
                      <p className="text-[10px] text-slate-500 font-mono truncate">
                        SHA-256: {ev.sha256} ({ev.size} bytes)
                      </p>
                    )}
                  </div>
                ))}
              </div>

              {/* Upload Evidence File Form */}
              <form onSubmit={handleUploadEvidence} className="space-y-1.5">
                <label className="text-[11px] text-slate-400 font-semibold">Upload File Evidence (PNG, JPG, JSON, TXT, LOG)</label>
                <div className="flex gap-2">
                  <input
                    type="file"
                    onChange={(e) => setEvidenceFile(e.target.files[0] || null)}
                    className="flex-1 text-xs text-slate-300 file:mr-2 file:py-1 file:px-2.5 file:rounded file:border-0 file:text-xs file:bg-slate-700 file:text-slate-200"
                  />
                  <button
                    type="submit"
                    disabled={!evidenceFile}
                    className="bg-blue-600 disabled:opacity-50 text-white px-2.5 py-1 rounded text-xs flex items-center gap-1"
                  >
                    <Upload className="w-3 h-3" /> Upload
                  </button>
                </div>
              </form>

              {/* Paste Text Evidence Form */}
              <form onSubmit={handlePasteEvidence} className="space-y-1.5 pt-2">
                <label className="text-[11px] text-slate-400 font-semibold">Or Paste Raw Request / Response / Note</label>
                <textarea
                  rows={2}
                  value={evidenceText}
                  onChange={(e) => setEvidenceText(e.target.value)}
                  placeholder="Paste HTTP request, logs, or proof-of-concept here..."
                  className="w-full bg-slate-700 text-white rounded p-2 text-xs border border-slate-600 focus:outline-none font-mono"
                />
                <button
                  type="submit"
                  disabled={!evidenceText.trim()}
                  className="bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-white px-3 py-1 rounded text-xs flex items-center gap-1"
                >
                  <FileText className="w-3 h-3" /> Save Note Evidence
                </button>
              </form>
            </div>
          </div>
        )}
      </div>

      {/* Create / Edit Finding Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 max-w-lg w-full space-y-4">
            <h3 className="text-lg font-bold text-white">
              {formData.id ? 'Edit Finding' : 'Create New Finding'}
            </h3>

            <form onSubmit={handleSubmitFinding} className="space-y-3 text-sm">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Title</label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g. Unauthenticated MySQL exposed on port 3306"
                  className="w-full bg-slate-700 text-white rounded px-3 py-1.5 border border-slate-600 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Severity</label>
                  <select
                    value={formData.severity}
                    onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
                    className="w-full bg-slate-700 text-white rounded px-2.5 py-1.5 border border-slate-600"
                  >
                    {SEVERITIES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full bg-slate-700 text-white rounded px-2.5 py-1.5 border border-slate-600"
                  >
                    {STATUSES.map((st) => (
                      <option key={st} value={st}>
                        {st}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Description</label>
                <textarea
                  rows={3}
                  value={formData.description || ''}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Detailed vulnerability or risk explanation..."
                  className="w-full bg-slate-700 text-white rounded p-2 border border-slate-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Notes / Remediation</label>
                <textarea
                  rows={2}
                  value={formData.notes || ''}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Internal notes or recommended fixes..."
                  className="w-full bg-slate-700 text-white rounded p-2 border border-slate-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Tags (comma-separated)</label>
                <input
                  type="text"
                  value={formData.tags || ''}
                  onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                  placeholder="e.g. database, remote-admin, sqli"
                  className="w-full bg-slate-700 text-white rounded px-3 py-1.5 border border-slate-600 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-700">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded"
                >
                  {formData.id ? 'Save Changes' : 'Create Finding'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

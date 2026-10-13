import { useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'
import {
  CheckSquare,
  CheckCircle2,
  Clock,
  Ban,
  Circle,
  FileEdit,
  PlusCircle,
  FolderKanban,
  Target as TargetIcon
} from 'lucide-react'

const STATES = [
  { value: 'NOT_STARTED', label: 'Not Started', color: 'bg-slate-700 text-slate-300 border-slate-600' },
  { value: 'IN_PROGRESS', label: 'In Progress', color: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40' },
  { value: 'COMPLETED', label: 'Completed', color: 'bg-green-500/20 text-green-300 border-green-500/40' },
  { value: 'NOT_APPLICABLE', label: 'N/A', color: 'bg-slate-800 text-slate-500 border-slate-700' },
]

export default function Checklist() {
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState('')
  const [targets, setTargets] = useState([])
  const [selectedTarget, setSelectedTarget] = useState('')
  const [progress, setProgress] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Editing note locally
  const [editingNotes, setEditingNotes] = useState({})
  const [savingId, setSavingId] = useState(null)

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

  // Load Targets when project changes
  useEffect(() => {
    if (!selectedProject) return
    const project = projects.find((p) => p.id === selectedProject)
    const tList = project?.targets || []
    setTargets(tList)
    if (tList.length > 0) {
      setSelectedTarget(tList[0].id)
    } else {
      setSelectedTarget('')
      setProgress([])
    }
  }, [selectedProject, projects])

  // Fetch Checklist Progress for target
  const fetchProgress = useCallback(async () => {
    if (!selectedTarget) return
    setLoading(true)
    setError(null)
    try {
      const data = await api.get(`/api/checklists/progress/${selectedTarget}`)
      setProgress(data)
      const noteMap = {}
      data.forEach((p) => {
        noteMap[p.id] = p.note || ''
      })
      setEditingNotes(noteMap)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [selectedTarget])

  useEffect(() => {
    fetchProgress()
  }, [fetchProgress])

  // Handle State Change
  const handleStateChange = async (progressId, newState) => {
    try {
      const updated = await api.patch(`/api/checklists/progress/${progressId}`, {
        state: newState,
        note: editingNotes[progressId],
      })
      setProgress((prev) => prev.map((item) => (item.id === progressId ? updated : item)))
    } catch (err) {
      setError(err.message)
    }
  }

  // Handle Note Save
  const handleSaveNote = async (progressId) => {
    setSavingId(progressId)
    try {
      const item = progress.find((p) => p.id === progressId)
      const updated = await api.patch(`/api/checklists/progress/${progressId}`, {
        state: item.state,
        note: editingNotes[progressId],
      })
      setProgress((prev) => prev.map((p) => (p.id === progressId ? updated : p)))
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingId(null)
    }
  }

  // Group items by Section
  const sections = {}
  progress.forEach((item) => {
    const sec = item.item_section || 'General'
    if (!sections[sec]) sections[sec] = []
    sections[sec].push(item)
  })

  // Calculation Metrics
  const totalItems = progress.length
  const completedItems = progress.filter((p) => p.state === 'COMPLETED').length
  const inProgressItems = progress.filter((p) => p.state === 'IN_PROGRESS').length
  const percentComplete = totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0

  return (
    <div className="p-6 space-y-6 text-slate-100">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <CheckSquare className="w-6 h-6 text-blue-400" /> Methodology Checklists
          </h1>
          <p className="text-sm text-slate-400">
            Systematic recon verification for Web, Network, and Database targets
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 px-3 py-1.5 rounded text-sm">
            <FolderKanban className="w-4 h-4 text-slate-400" />
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="bg-transparent text-white focus:outline-none"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id} className="bg-slate-800">
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 px-3 py-1.5 rounded text-sm">
            <TargetIcon className="w-4 h-4 text-slate-400" />
            <select
              value={selectedTarget}
              onChange={(e) => setSelectedTarget(e.target.value)}
              disabled={targets.length === 0}
              className="bg-transparent text-white focus:outline-none disabled:opacity-50"
            >
              {targets.length === 0 ? (
                <option value="">No Targets Configured</option>
              ) : (
                targets.map((t) => (
                  <option key={t.id} value={t.id} className="bg-slate-800">
                    {t.value}
                  </option>
                ))
              )}
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/50 border border-red-500 text-red-200 text-sm px-4 py-3 rounded">
          {error}
        </div>
      )}

      {targets.length === 0 ? (
        <div className="bg-slate-800/80 border border-slate-700 rounded-lg p-8 text-center space-y-3">
          <TargetIcon className="w-10 h-10 text-slate-500 mx-auto" />
          <h3 className="text-lg font-semibold text-white">No targets found for this project</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto">
            Checklists track testing methodology per specific target. Head over to the Projects page to add target domains, IPs, or CIDRs first.
          </p>
        </div>
      ) : (
        <>
          {/* Progress Overview Bar */}
          <div className="bg-slate-800 rounded-lg p-5 border border-slate-700 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-white">Overall Checklist Completion</h3>
                <p className="text-xs text-slate-400">
                  {completedItems} of {totalItems} items completed ({inProgressItems} in progress)
                </p>
              </div>
              <span className="text-2xl font-bold text-blue-400">{percentComplete}%</span>
            </div>

            <div className="w-full bg-slate-700 h-2.5 rounded-full overflow-hidden">
              <div
                className="bg-blue-500 h-full transition-all duration-300"
                style={{ width: `${percentComplete}%` }}
              />
            </div>
          </div>

          {/* Checklist Sections */}
          {loading ? (
            <p className="p-8 text-center text-slate-400">Loading checklist items...</p>
          ) : (
            <div className="space-y-6">
              {Object.entries(sections).map(([sectionName, items]) => (
                <div key={sectionName} className="bg-slate-800 rounded-lg border border-slate-700/60 overflow-hidden">
                  <div className="bg-slate-900/80 px-5 py-3 border-b border-slate-700/60 flex items-center justify-between">
                    <h3 className="font-semibold text-slate-200 text-sm tracking-wide uppercase">
                      {sectionName}
                    </h3>
                    <span className="text-xs text-slate-400">
                      {items.filter((i) => i.state === 'COMPLETED').length}/{items.length} Done
                    </span>
                  </div>

                  <div className="divide-y divide-slate-700/40">
                    {items.map((item) => (
                      <div key={item.id} className="p-4 hover:bg-slate-700/20 transition-colors space-y-2">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                          <span className="text-sm text-slate-100 font-medium">{item.item_title}</span>

                          {/* State Selector Buttons */}
                          <div className="flex items-center gap-1.5">
                            {STATES.map((st) => (
                              <button
                                key={st.value}
                                onClick={() => handleStateChange(item.id, st.value)}
                                className={`text-xs px-2.5 py-1 rounded font-medium border transition-colors ${
                                  item.state === st.value
                                    ? st.color
                                    : 'bg-slate-800/80 text-slate-400 border-slate-700 hover:bg-slate-700'
                                }`}
                              >
                                {st.label}
                              </button>
                            ))}
                          </div>
                        </div>

                        {/* Note Input */}
                        <div className="flex gap-2 pt-1">
                          <input
                            type="text"
                            placeholder="Add findings note or observations..."
                            value={editingNotes[item.id] || ''}
                            onChange={(e) =>
                              setEditingNotes({
                                ...editingNotes,
                                [item.id]: e.target.value,
                              })
                            }
                            className="flex-1 bg-slate-900/60 text-slate-300 text-xs rounded px-3 py-1.5 border border-slate-700/80 focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                          {editingNotes[item.id] !== (item.note || '') && (
                            <button
                              onClick={() => handleSaveNote(item.id)}
                              disabled={savingId === item.id}
                              className="bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1 rounded font-medium"
                            >
                              {savingId === item.id ? 'Saving...' : 'Save Note'}
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

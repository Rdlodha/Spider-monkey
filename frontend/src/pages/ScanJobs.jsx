import { useState, useEffect, useRef } from 'react'
import { Play, XCircle, RefreshCw, ChevronDown, ChevronUp, Loader2, Terminal } from 'lucide-react'
import { api } from '../services/api'

const STATUS_COLORS = {
  queued: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
  running: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  completed: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  cancelled: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
}

function StatusBadge({ status }) {
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${STATUS_COLORS[status] || ''}`}>
      {status}
    </span>
  )
}

function LogViewer({ url, label }) {
  const [text, setText] = useState(null)
  const [open, setOpen] = useState(false)

  const load = async () => {
    if (!url) return
    try {
      const resp = await fetch(url, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      })
      setText(await resp.text())
    } catch {
      setText('(failed to load)')
    }
  }

  const toggle = () => {
    if (!open && text === null) load()
    setOpen(o => !o)
  }

  if (!url) return null
  return (
    <div className="mt-2">
      <button
        onClick={toggle}
        className="flex items-center gap-1 text-xs text-blue-500 hover:underline"
      >
        <Terminal className="w-3 h-3" />
        {label}
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      {open && (
        <pre className="mt-1 bg-slate-950 text-emerald-400 text-xs rounded-lg p-3 max-h-64 overflow-auto whitespace-pre-wrap">
          {text ?? 'Loading…'}
        </pre>
      )}
    </div>
  )
}

function JobRow({ job, onCancel }) {
  const [expanded, setExpanded] = useState(false)
  const canCancel = job.status === 'queued' || job.status === 'running'

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 space-y-2">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3 flex-wrap">
          <StatusBadge status={job.status} />
          <span className="font-mono text-xs text-slate-500 dark:text-slate-400">{job.id.slice(0, 8)}…</span>
          <span className="font-medium dark:text-white">{job.tool}</span>
          <span className="text-xs text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded">{job.profile}</span>
          {job.exit_code !== null && (
            <span className="text-xs text-slate-500 dark:text-slate-400">exit {job.exit_code}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {job.status === 'running' && <Loader2 className="w-4 h-4 animate-spin text-blue-500" />}
          {canCancel && (
            <button
              onClick={() => {
                if (confirm('Cancel this job?')) onCancel(job.id)
              }}
              className="flex items-center gap-1 text-xs px-2 py-1 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded hover:bg-red-100 dark:hover:bg-red-900/40"
            >
              <XCircle className="w-3 h-3" />
              Cancel
            </button>
          )}
          <button onClick={() => setExpanded(e => !e)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="text-xs text-slate-500 dark:text-slate-400 space-y-1 pt-1 border-t border-slate-100 dark:border-slate-700">
          <p>Started: {job.started_at ? new Date(job.started_at).toLocaleString() : '—'}</p>
          <p>Completed: {job.completed_at ? new Date(job.completed_at).toLocaleString() : '—'}</p>
          <LogViewer url={job.stdout_url ? `/api${job.stdout_url}` : null} label="stdout" />
          <LogViewer url={job.stderr_url ? `/api${job.stderr_url}` : null} label="stderr" />
        </div>
      )}
    </div>
  )
}

export default function ScanJobs() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState('all')
  const pollRef = useRef(null)

  const load = async () => {
    try {
      // The engine router lists all jobs for all projects
      // We call a broader endpoint; for now we fetch by page using project_id from query
      const data = await api.get('/engine/jobs')
      setJobs(data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // Poll every 4 s when there are running/queued jobs
    pollRef.current = setInterval(() => {
      setJobs(prev => {
        const hasActive = prev.some(j => j.status === 'running' || j.status === 'queued')
        if (hasActive) load()
        return prev
      })
    }, 4000)
    return () => clearInterval(pollRef.current)
  }, [])

  const handleCancel = async (id) => {
    try {
      await api.post(`/engine/jobs/${id}/cancel`, {})
      load()
    } catch (e) {
      alert(e.message || 'Failed to cancel')
    }
  }

  const filtered = filterStatus === 'all' ? jobs : jobs.filter(j => j.status === filterStatus)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Play className="w-6 h-6 text-blue-500" />
          <h1 className="text-2xl font-bold dark:text-white">Scan Jobs</h1>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm dark:bg-slate-800 dark:text-white"
          >
            <option value="all">All statuses</option>
            {['queued', 'running', 'completed', 'failed', 'cancelled'].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <button
            onClick={load}
            className="p-1.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-white"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-blue-500" /></div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-slate-500 dark:text-slate-400">
          <Play className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>No scan jobs yet. Request a scan from the Scans page to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(job => (
            <JobRow key={job.id} job={job} onCancel={handleCancel} />
          ))}
        </div>
      )}
    </div>
  )
}
